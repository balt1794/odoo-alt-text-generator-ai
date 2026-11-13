# -*- coding: utf-8 -*-
{
    'name': 'Alt Text Generator AI',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Generate SEO-friendly alt text for your website images with AI',
    'description': """
Alt Text Generator AI
=====================
Writes descriptive, SEO-friendly alt text for the images on your Odoo website
pages with AI, in 131 languages.
""",
    'author': 'AltTextGeneratorAI',
    'website': 'https://alttextgeneratorai.com',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/website_page_views.xml',
        'views/alt_text_bulk_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'alt_text_generator_ai/static/src/scss/bulk.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
}
