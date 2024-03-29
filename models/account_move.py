import ast

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    related_orders = fields.Many2many('sale.order', compute='_compute_related_orders')
    bonuses_ids = fields.Many2many('gse.bonus', compute='_compute_related_orders')
    bonuses_count = fields.Integer(string='# Bonuses', compute='_compute_related_orders', groups="account.group_account_manager")

    @api.depends('line_ids.sale_line_ids.order_id')
    def _compute_related_orders(self):
        for move in self:
            related_orders = move.line_ids.sale_line_ids.order_id
            move.related_orders = related_orders
            move.bonuses_ids = related_orders.bonuses_ids
            move.bonuses_count = len(related_orders.bonuses_ids)

    def action_view_bonuses(self):
        action = self.env['ir.actions.act_window']._for_xml_id('technicians.action_gse_bonus')
        action['display_name'] = self.name
        action['domain'] = [('id', 'in', self.bonuses_ids.ids)]
        context = action['context'].replace('active_id', str(self.id))
        action['context'] = ast.literal_eval(context)
        return action

    def _invoice_paid_hook(self):
        res = super()._invoice_paid_hook()
        for move in self:
            if move.move_type == 'out_refund':
                # Special case for paid credit note: generate a negative bonus
                move.bonuses_ids.revert()
            else:
                for order in move.related_orders:
                    self.env['gse.bonus'].generate_bonuses(order)
        return res

    def write(self, vals):
        # In case of cancel or draft of invoices which is coming from the
        # "posted" state -> "Cancel" the bonuses
        if 'state' in vals and vals['state'] != 'posted':
            for move in self.filtered(lambda m: m.state == 'posted'):
                move.bonuses_ids.revert()

        return super().write(vals)
