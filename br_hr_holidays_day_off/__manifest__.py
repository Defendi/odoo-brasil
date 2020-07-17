{
    'name': 'Brazilian days off',
    'version': '11.0.0.0',
    'category': 'Human Resources',
    'license': 'AGPL-3',
    'author': 'DocSafe',
    'website': 'http://www.docsafe.com.br',
    'contributors': [
        'Alexandre Defendi <alexandre_defendi@hotmail.com>',
    ],
    'depends': ['hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_holidays_imposed_view.xml',
        'data/br_days_off.xml',
    ],
    'installable': True,
}
