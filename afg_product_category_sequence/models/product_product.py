from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    auto_check = fields.Boolean(
        'Auto Check',
        compute='_compute_auto_check',
        store=True
    )

    sequence_generated = fields.Boolean(
        'Sequence Generated',
    )

    # ---------------------------------------------------------
    # UNIQUE DEFAULT CODE (Variant Level)
    # ---------------------------------------------------------
    @api.constrains('default_code')
    def unique_default_code(self):
        for product in self.filtered(lambda p: p.default_code):
            duplicate = self.search([
                ('default_code', '=', product.default_code),
                ('id', '!=', product.id)
            ], limit=1)
            if duplicate:
                raise UserError(_(
                    'These products: %s and %s have the same default code'
                ) % (product.display_name, duplicate.display_name))


    # ---------------------------------------------------------
    # COMPUTE AUTO CHECK
    # ---------------------------------------------------------
    @api.depends('product_tmpl_id.categ_id.sequence_mode',
                 'product_tmpl_id.categ_id.sequence_id')
    def _compute_auto_check(self):
        for rec in self:
            category = rec.product_tmpl_id.categ_id
            rec.auto_check = bool(
                category and
                category.sequence_mode == 'automatic' and
                category.sequence_id
            )


    @api.model
    def name_create(self, name):

        category = self.env.context.get('default_categ_id')

        # Convert record → id safely
        if category:
            if isinstance(category, models.BaseModel):
                category_id = category.id
            else:
                category_id = category
        else:
            category_id = self.env.ref('product.product_category_all').id

        template = self.env['product.template'].create({
            'name': name,
            'categ_id': category_id,
        })

        return (template.product_variant_id.id, template.display_name)


