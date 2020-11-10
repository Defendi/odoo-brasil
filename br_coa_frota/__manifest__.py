# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{  # pylint: disable=C8101,C8103
    'name': 'Plano de Contas Frota',
    'summary': """Plano de contas Frota""",
    'description': """Plano de contas Brasileiro Frota""",
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
    ],
    'depends': [
        'account', 'br_account'
    ],
    'data': [
        'data/account.group.csv',
        'data/br_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_template_data.xml',
    ],
    'active': True,
}
