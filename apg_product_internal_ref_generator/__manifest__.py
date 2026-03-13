# -*- coding: utf-8 -*-

{
    "name": "Product Internal Reference Generator",
    "version": "18.0.0.0",
    "category": "Warehouse",
    "summary": """Automatically generate and assign unique internal reference codes to products in Odoo, ensuring consistent product identification and reducing manual entry errors.""",
    "description": """Automatically generate and assign unique internal reference codes to products in Odoo, ensuring consistent product identification and reducing manual entry errors.""",
    'author': 'Apagen Solutions Pvt Ltd',
    'company': 'Apagen Solutions Pvt Ltd',
    'maintainer': 'Apagen Solutions Pvt Ltd',
    'website': "https://www.apagen.com",
    "depends": ["sale_management"],
    "data": [
        'data/ir_sequence_data.xml',
        'data/ir_actions_server_data.xml',
        'views/res_config_settings_views.xml',
    ],
    "images": ["static/description/banner.jpg"],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
