# -*- coding: utf-8 -*-
from odoo import fields, models

class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = 'Message Wizard'

    message = fields.Text('Message', required=True, readonly=True)

    def action_ok(self):
        """ Close the wizard """
        return {'type': 'ir.actions.act_window_close'}
