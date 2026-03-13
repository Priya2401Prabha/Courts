# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """ Inherit the configuration settings to add fields """
    _inherit = 'res.config.settings'

    pro_internal_ref = fields.Boolean(string='Product Internal Ref',
                                      help="Internal reference of products",
                                      config_parameter='apg_product_internal_ref_generator.pro_internal_ref')
    auto_generate_internal_ref = fields.Boolean(
        string='Auto Generate Product Internal Ref',
        help="To auto generate the product internal reference.",
        config_parameter='apg_product_internal_ref_generator.auto_generate_internal_ref')
    product_name_config = fields.Boolean(string='Product Name Config',
                                         help="Name of the product config",
                                         config_parameter='apg_product_internal_ref_generator.product_name_config')
    pro_name_digit = fields.Integer(string='Product Name Digit',
                                    help="Number of digit of product name",
                                    config_parameter='apg_product_internal_ref_generator.pro_name_digit')
    pro_name_separator = fields.Char(string='Product Name Separator',
                                     help="Separator for product name",
                                     config_parameter='apg_product_internal_ref_generator.pro_name_separator')
    pro_template_config = fields.Boolean(string='Product Attribute Config',
                                         help="To add the product attribute config",
                                         config_parameter='apg_product_internal_ref_generator.pro_template_config')
    pro_template_digit = fields.Integer(string='Product Attribute Digit',
                                        help="Number of digit of product attribute",
                                        config_parameter='apg_product_internal_ref_generator.pro_template_digit')
    pro_template_separator = fields.Char(string='Product Attribute Separator',
                                         help="Separator for product attribute",
                                         config_parameter="apg_product_internal_ref_generator.pro_template_separator")
    pro_categ_config = fields.Boolean(string='Product Category Config',
                                      help="To add product category",
                                      config_parameter="apg_product_internal_ref_generator.pro_categ_config")
    pro_categ_digit = fields.Integer(string='Product Category Digit',
                                     help="Number of product category digit",
                                     config_parameter='apg_product_internal_ref_generator.pro_categ_digit')
    pro_categ_separator = fields.Char(string='Product Category Separator',
                                      help="Separator for product category",
                                      config_parameter='apg_product_internal_ref_generator.pro_categ_separator')
