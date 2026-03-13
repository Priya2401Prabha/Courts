# -*- coding: utf-8 -*-

from odoo import api, models


class ProductProduct(models.Model):
    """ Class for products to generate the internal reference """
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        """ Supering the create function, generating the internal reference """
        res = super().create(vals_list)
        if 'default_code' in vals_list:
            pass
        else:
            auto_generate_internal_ref = self.env[
                'ir.config_parameter'].sudo().get_param(
                'apg_product_internal_ref_generator.auto_generate_internal_ref')
            if auto_generate_internal_ref:
                product_name_config = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.product_name_config')
                pro_name_digit = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.pro_name_digit')
                pro_name_separator = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.pro_name_separator')
                pro_categ_config = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.pro_categ_config')
                pro_categ_digit = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.pro_categ_digit')
                pro_categ_separator = self.env[
                    'ir.config_parameter'].sudo().get_param(
                    'apg_product_internal_ref_generator.pro_categ_separator')
                for rec in res:
                    default_code = ''
                    if rec.type == 'consu':
                        default_code += 'Goods:'
                    elif rec.type == 'service':
                        default_code += 'Service:'
                    elif rec.type == 'combo':
                        default_code += 'Combo:'
                    if product_name_config:
                        if rec.name:
                            default_code += rec.name[:int(pro_name_digit)]
                            default_code += pro_name_separator
                    if pro_categ_config:
                        if rec.categ_id.name:
                            default_code += rec.categ_id.name[
                                            :int(pro_categ_digit)]
                            default_code += pro_categ_separator
                    sequence_code = 'product.sequence.ref'
                    default_code += self.env['ir.sequence'].next_by_code(
                        sequence_code)
                    rec.default_code = default_code
        return res

    @api.model
    def action_generate_internal_ref_pro(self):
        """ Creating the internal reference """
        active_ids = self.env.context.get('active_ids')
        products = self.env['product.product'].browse(active_ids)
        product_name_config = self.env[
            'ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.product_name_config')
        pro_name_digit = self.env['ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.pro_name_digit')
        pro_name_separator = self.env[
            'ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.pro_name_separator')
        pro_categ_config = self.env['ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.pro_categ_config')
        pro_categ_digit = self.env['ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.pro_categ_digit')
        pro_categ_separator = self.env[
            'ir.config_parameter'].sudo().get_param(
            'apg_product_internal_ref_generator.pro_categ_separator')
        for rec in products:
            if not rec.default_code:
                default_code = ''
                if rec.type == 'consu':
                    default_code += 'Goods:'
                elif rec.type == 'service':
                    default_code += 'Service:'
                elif rec.type == 'combo':
                    default_code += 'Combo:'
                if product_name_config:
                    if rec.name:
                        default_code += rec.name[:int(pro_name_digit)]
                        default_code += pro_name_separator
                if pro_categ_config:
                    if rec.categ_id.name:
                        default_code += rec.categ_id.name[:int(pro_categ_digit)]
                        default_code += pro_categ_separator
                sequence_code = 'product.sequence.ref'
                default_code += self.env['ir.sequence'].next_by_code(
                    sequence_code)
                rec.default_code = default_code
        return self
