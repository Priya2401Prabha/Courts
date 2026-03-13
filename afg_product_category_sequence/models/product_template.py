from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    auto_check = fields.Boolean(
        'Auto Check',
        compute='_compute_auto_check',
        store=True
    )
    sequence_generated = fields.Boolean(
        'Sequence Generated',
    )

    @api.constrains('default_code')
    def unique_default_code(self):
        for product in self.filtered(lambda p: p.default_code):
            product_with_same_code = self.env['product.template'].search(
                [('default_code', '=', product.default_code), ('id', '!=', product.id)])
            if product_with_same_code:
                raise UserError(_('These product templates: %s, %s have the same default code') % (
                product.display_name, product_with_same_code.display_name))


    @api.depends('categ_id', 'categ_id.sequence_mode', 'categ_id.sequence_id')
    def _compute_auto_check(self):
        for rec in self:
            if rec.categ_id and \
                    rec.categ_id.sequence_mode == 'automatic' and \
                    rec.categ_id.sequence_id:
                rec.auto_check = True
            else:
                rec.auto_check = False

    @api.model
    def create(self, vals):

        category_id = vals.get('categ_id')

        # 🔥 SAFELY CONVERT RECORD → ID
        if category_id:
            if isinstance(category_id, models.BaseModel):
                category_id = category_id.id
            else:
                category_id = int(category_id)

        else:
            # Default fallback
            default_cat = self.env.ref('product.product_category_all', raise_if_not_found=False)
            category_id = default_cat.id if default_cat else False

        if category_id:
            category = self.env['product.category'].browse(category_id)

            if category.exists() and \
                    category.sequence_mode == 'automatic' and \
                    category.sequence_id:

                next_seq = category.sequence_id.next_by_id()

                if not next_seq:
                    raise UserError(
                        f"Failed to generate sequence for category {category.name}"
                    )

                vals['default_code'] = str(next_seq)
                vals['sequence_generated'] = True
            else:
                vals['sequence_generated'] = False

        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)

        if 'categ_id' in vals:
            for rec in self:
                category = rec.categ_id

                if category.sequence_mode == 'automatic' and category.sequence_id:
                    # Generate new sequence only if:
                    # 1. Product had auto-generated code
                    # OR
                    # 2. Category is automatic
                    rec.default_code = category.sequence_id.next_by_id()
                    rec.sequence_generated = True

                elif category.sequence_mode == 'manual':
                    # If manual, allow user to edit
                    rec.sequence_generated = False

        return res


    # def write(self, vals):
    #     # Track manual override
    #     if 'default_code' in vals:
    #         for rec in self:
    #             if rec.sequence_generated:
    #                 vals['sequence_override'] = True
    #     return super().write(vals)
