# -*- coding: utf-8 -*-
{
    'name': "Raisa - Market Basket Analysis",

    'summary': """
        Market Basket Analysis""",

    'description': """
        Hackathon Pintar - Market Basket Analysis
    """,

    'author': "Fahmi Roihanul Firdaus & Muhammad Syarif",
    'maintainer': 'Raisa Team',
    'website': "http://www.warungpintar.co.id",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'images': ['static/description/icon.png'],
    # any module necessary for this one to work correctly
    'depends': ['base','sale','stock'],

    # always loaded
    'data': [
        'wizard/market_basket_analysis_views.xml'
    ]
}