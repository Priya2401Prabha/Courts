from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    sequence_mode = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')
    ], string='Sequence Mode', required=True)

    sequence_id = fields.Many2one('ir.sequence', string='Internal Reference Sequence')
    category_code = fields.Char('Category Code', index=True, tracking=True)
    sequence_lock = fields.Boolean('Sequence Locked', default=False)

    @api.constrains('category_code')
    def _check_unique_category_code(self):
        for rec in self:
            if not rec.category_code:
                continue

            existing = self.search([
                ('id', '!=', rec.id),
                ('category_code', '=', rec.category_code)
            ], limit=1)

            if existing:
                raise UserError(_("Category Code must be unique."))

    # -----------------------------------------------------
    # ONCHANGE PARENT
    # -----------------------------------------------------
    @api.onchange('parent_id')
    def _onchange_parent_category(self):
        for rec in self:
            if not rec.parent_id:
                rec.sequence_lock = False
                return

            parent = rec.parent_id

            # Inherit parent mode (LOCKED behavior)
            rec.sequence_mode = parent.sequence_mode
            rec.sequence_lock = True

            # If automatic → generate next child code
            if parent.sequence_mode == 'automatic':
                parent_code = parent.category_code or ''

                if not parent_code:
                    raise UserError(_("Parent category must have a Category Code."))

                # Fetch existing children
                children = self.search([
                    ('parent_id', '=', parent.id),
                    ('category_code', '!=', False)
                ])

                suffix_numbers = []

                for child in children:
                    if child.category_code.startswith(parent_code):
                        suffix = child.category_code[len(parent_code):]
                        if suffix.isdigit():
                            suffix_numbers.append(int(suffix))

                next_number = max(suffix_numbers) + 1 if suffix_numbers else 1

                # Minimum 2 digits, dynamic growth
                rec.category_code = f"{parent_code}{str(next_number).zfill(2)}"

    def action_generate_all_child_sequences(self):
        """
        Generate hierarchical category_code for all automatic families.
        Works for multi-level category trees.
        """

        parents = self.search([
            ('sequence_mode', '=', 'automatic'),
            ('parent_id', '=', False)
        ])

        for parent in parents:
            self._generate_child_codes_recursive(parent)

    def _generate_child_codes_recursive(self, parent):
        """
        Recursive generator for hierarchical categories
        """

        if not parent.category_code:
            return

        children = self.search([
            ('parent_id', '=', parent.id)
        ], order='id')

        suffix_numbers = []

        # Collect existing numbers for this parent only
        for child in children:
            if child.category_code and child.category_code.startswith(parent.category_code):
                suffix = child.category_code[len(parent.category_code):]
                if suffix.isdigit() and len(suffix) == 2:
                    suffix_numbers.append(int(suffix))

        next_number = max(suffix_numbers) + 1 if suffix_numbers else 1

        for child in children:

            # Generate if missing
            if not child.category_code:
                new_code = f"{parent.category_code}{str(next_number).zfill(2)}"
                child.write({
                    'category_code': new_code,
                    'sequence_mode': parent.sequence_mode,
                    'sequence_lock': True
                })
                next_number += 1

            # Recursive call for subchildren
            self._generate_child_codes_recursive(child)

    # -----------------------------------------------------
    # CREATE
    # -----------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('parent_id'):
            parent = self.env['product.category'].browse(vals['parent_id'])

            # Force inherit parent mode
            vals['sequence_mode'] = parent.sequence_mode
        record = super().create(vals)

        # Ensure sequence only if automatic
        if record.sequence_mode == 'automatic':
            record._ensure_sequence()

        return record

    # -----------------------------------------------------
    # WRITE
    # -----------------------------------------------------
    def write(self, vals):
        if 'parent_id' in vals and vals['parent_id']:
            parent = self.env['product.category'].browse(vals['parent_id'])
            vals['sequence_mode'] = parent.sequence_mode
        res = super().write(vals)

        for rec in self:
            if rec.sequence_mode == 'automatic':
                rec._ensure_sequence()

        return res

    # -----------------------------------------------------
    # ENSURE SEQUENCE
    # -----------------------------------------------------
    def _ensure_sequence(self):
        """
        Automatically create/update sequence
        when category is set to Automatic.
        """
        for rec in self:
            if rec.sequence_mode != 'automatic':
                continue

            if not rec.category_code:
                raise UserError(_("Please set a Category Code before using Automatic mode."))

            if not rec.sequence_id:
                seq_code = f"product_category_{rec.id}_seq"

                seq_vals = {
                    'name': f"{rec.name} - Category Sequence",
                    'code': seq_code,
                    'prefix': rec.category_code,
                    'padding': 4,
                    'company_id': self.env.company.id,
                }

                sequence = self.env['ir.sequence'].create(seq_vals)
                rec.sequence_id = sequence.id

            else:
                # Update prefix if category code changes
                rec.sequence_id.prefix = rec.category_code