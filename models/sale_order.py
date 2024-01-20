# -*- coding: utf-8 -*-

import ast

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bonuses_ids = fields.One2many('gse.bonus', 'order_id')
    bonuses_count = fields.Integer(string='# Bonuses', compute='_compute_bonuses_count', groups="account.group_account_manager")

    bonus_state = fields.Selection([
        ('not_invoiced', 'Not Invoiced'), 
        ('not_paid', 'Invoices Not Paid'), 
        ('not_delivered', 'Products Not Delivered'),
        ('no_services', 'No Services Related to this SO'),
        ('not_all_services_given', 'Services not rendered'),
        ('no_timesheet', 'No Timesheet'),
        ('no_transport_allowed', 'No Transport'),
        ('not_finished', 'Taches pas finies' )
        ], 
        default='not_invoiced',
        help='Not Invoiced = not all product have been invoiced',
        tracking=True)

    @api.depends('bonuses_ids')
    def _compute_bonuses_count(self):
        for order in self:
            order.bonuses_count = len(order.bonuses_ids)

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
