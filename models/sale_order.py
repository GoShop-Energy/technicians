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
            # TODO: no_transport_allowed is related to the employee contract in your initial PR, but it's weird because a SO could have a bonus
            #       granted for other employees for this SO, this bonus state shouldn't be employee dependant but "global" to the SO.
            #       Maybe you meant to target the field on task which disable the bonuses and not the employee one?
            ('no_transport_allowed', 'No Transport'),
            # TODO: no_timesheet is also weird because it is SO LINE related, not SO related, so if you have 2 tasks on the same SO, one has bonuses
            #       but the other doesn't, what do you expect as value here? Bonus granted or "no_timesheet" to let people know something is
            #       blocking? Both would neither be true neither be wrong.
            # TODO: For both TODO above, you can actually see that something is wrong because in your commit, you set the order bonus state
            #       in a loop, so depending of the loop iteration, the order state change, which is not what you want. There should only be one
            #       true value for the order bonus state.
            ('no_timesheet', 'No Timesheet'),
            # ('not_finished', 'Task Not Done')  # TODO: Not needed normally, see below TODO next to "not_delivered"
        ], default='not_invoiced',
        help='Not Invoiced = not all product have been invoiced', tracking=True,
        store=True, compute='_compute_bonus_state',
    )

    @api.depends('bonuses_ids')
    def _compute_bonuses_count(self):
        for order in self:
            order.bonuses_count = len(order.bonuses_ids)

    @api.depends('date_order, order_line.qty_invoiced, order_line.product_uom_qty, invoice_ids.payment_state, order_line.product_id.service_tracking, order_line.qty_delivered, order_line.is_downpayment, order_line.display_type')
    def _compute_bonus_state(self):
        for order in self:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if not (order.date_order > fields.Datetime.from_string('2023-05-31 23:59:59')):
                order.bonus_state = 'before_2023_05_31'
            elif any(line for line in order.order_line if line.product_uom_qty != line.qty_invoiced):
                order.bonus_state = 'not_invoiced'
            elif any(move_state not in ('paid', 'reversed') for move_state in order.invoice_ids.mapped('payment_state')):
                order.bonus_state = 'not_paid'
            elif not any(line.product_id.service_tracking != 'no' for line in order.order_line):
                order.bonus_state = 'no_services'
            elif not order.order_line.filtered(
                lambda line:
                not (line.is_downpayment or line.display_type or (line.product_id.type == 'service' and line.product_id.service_tracking == 'no'))
                and float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) >= 0
            ):
                # TODO: confirm this or tell me if need more precise but a service_tracking line will be set as delivered when the task is done
                #       so this should/will also cover the case of take not set as Done
                order.bonus_state = 'not_delivered'

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
