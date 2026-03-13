# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date
from odoo.addons.stock_landed_costs.models.stock_landed_cost import SPLIT_METHOD


if ("by_percentage", "By Percentage") not in SPLIT_METHOD:
    SPLIT_METHOD.append(("by_percentage", "By Percentage"))


class ProductTemplate(models.Model):
    _inherit = "product.template"

    split_method_landed_cost = fields.Selection(
        selection=SPLIT_METHOD,
        string="Default Split Method",
        help="Default Split Method when used for Landed Cost",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    avg_cost = fields.Float(string="Average Cost", digits="Product Price")
    landed_cost = fields.Float(string="Landed Cost", digits="Product Price")
    prev_landed_cost = fields.Float(string="Previous Landed Cost", digits="Product Price")

    approve_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approval", "Approval"),
            ("approved", "Approved"),
        ],
        default="draft",
        tracking=True,
    )

    approver_user_id = fields.Many2one(
        "res.users",
        string="Approver",
        tracking=True,
    )

    user_approval_id = fields.Many2one(
        "res.users",
        string="Requester",
        tracking=True,
    )

    approved_date = fields.Date(string="Approved Date", readonly=True)
    is_duty = fields.Boolean(string="Is Duty", default=False)

    # ---------------- ACTIONS ---------------- #

    def product_approved(self):
        template = self.env.ref(
            "afg_stock_landed_cost.send_approved_mail",
            raise_if_not_found=False,
        )
        for rec in self:
            if template:
                template.send_mail(rec.id, force_send=True)
            rec.write({
                "approver_user_id": self.env.user.id,
                "approved_date": date.today(),
                "approve_state": "approved",
            })

    def product_approval(self):
        template = self.env.ref(
            "afg_stock_landed_cost.send_approval_mail",
            raise_if_not_found=False,
        )

        group = self.env.ref(
            "afg_stock_landed_cost.product_cost_manager",
            raise_if_not_found=False,
        )

        email_to = ",".join(
            user.email
            for user in group.users
            if user.email and user.id != 2
        ) if group else ""

        for rec in self:
            if template:
                template.email_to = email_to
                template.send_mail(rec.id, force_send=True)
            rec.write({
                "user_approval_id": self.env.user.id,
                "approve_state": "approval",
            })

    def reset_product_draft(self):
        self.write({"approve_state": "draft"})

    # ---------------- ORM OVERRIDE ---------------- #

    def write(self, vals):
        if "standard_price" in vals:
            self.update({"avg_cost": self.standard_price})
        return super().write(vals)
