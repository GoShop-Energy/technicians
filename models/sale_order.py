# -*- coding: utf-8 -*-

import ast

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bonuses_ids = fields.One2many('gse.bonus', 'order_id')
    bonuses_count = fields.Integer(string='# Bonuses', compute='_compute_bonuses_count', groups="account.group_account_manager")
    bonus_state = fields.Selection(
        [
            ('before_2023_05_31', 'Not Invoiced'),
            ('not_invoiced', 'Not Invoiced'),
            ('not_paid', 'Invoices Not Paid'),
            ('not_delivered', 'Products Not Delivered'),
            ('no_services', 'No Services Related to this SO'),
            ('not_all_services_given', 'Services not rendered'),
            ('task_not_set_as_done', 'Task not set as done'),
            ('something_missing', 'Something Missing (task or employee contract disallow transport expenses?)'),
            ('done', 'Granted'),
        ], default='not_invoiced',
        help='Not Invoiced = not all product have been invoiced', tracking=True,
        store=True, compute='_compute_bonus_state',
    )

    @api.depends('bonuses_ids')
    def _compute_bonuses_count(self):
        for order in self:
            order.bonuses_count = len(order.bonuses_ids)

    @api.depends('date_order', 'bonuses_count', 'order_line.qty_invoiced', 'order_line.product_uom_qty', 'invoice_ids.payment_state', 'order_line.product_id.service_tracking', 'order_line.qty_delivered', 'order_line.is_downpayment', 'order_line.display_type')
    def _compute_bonus_state(self):
        for order in self:
            if order.bonuses_count:
                order.bonus_state = 'done'
                continue

            state = None
            if not (order.date_order > fields.Datetime.from_string('2023-05-31 23:59:59')):
                state = 'before_2023_05_31'
            elif any(line for line in order.order_line if line.product_uom_qty != line.qty_invoiced):
                state = 'not_invoiced'
            elif any(move_state not in ('paid', 'reversed') for move_state in order.invoice_ids.mapped('payment_state')):
                state = 'not_paid'
            elif not any(line.product_id.service_tracking != 'no' for line in order.order_line):
                state = 'no_services'
            else:
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                for line in order.order_line.filtered(lambda l: not (l.is_downpayment or l.display_type)):
                    if line.product_id.type == 'service' and line.product_id.service_tracking != 'no':
                        if line.qty_delivered == 0:
                            state = 'not_all_services_given'
                        elif line.task_id.stage_id.with_context(lang='en_US').name != "Done":
                            state = 'task_not_set_as_done'
                    elif line.product_id.type == 'service' and line.product_id.service_policy == 'ordered_prepaid':
                        # prepaid service will/could remain at 0 delivered qty but it's
                        # normal and should not block the bonus
                        pass
                    else:
                        if not float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) >= 0:
                            state = 'not_delivered'

            order.bonus_state = state or 'something_missing'

    def action_view_bonuses(self):
        action = self.env['ir.actions.act_window']._for_xml_id('technicians.action_gse_bonus')
        action['display_name'] = self.name
        action['domain'] = [('id', 'in', self.bonuses_ids.ids)]
        context = action['context'].replace('active_id', str(self.id))
        action['context'] = ast.literal_eval(context)
        return action

    def action_cancel(self):
        if any(m.payment_state == 'posted' for m in self.bonuses_ids.vendor_bill_move_ids):
            raise UserError('Cette vente est liée à une commission qui a déjà été payée.')

        self.bonuses_ids.unlink()

        return super().action_cancel()

    def regenerate_bonuses(self):
        # Called through the action on form view
        for order in self:
            self.env['gse.bonus'].generate_bonuses(order)
