{
    'name': 'CNAB return files',
    'summary': """Base Module for the Brazilian Cnab Return Files""",
    'description': """Base Module for the Brazilian Cnab Return Files""",
    'version': '0.0.1',
    'category': 'account',
    'author': 'Alexandre Defendi',
    'license': 'AGPL-3',
    'website': 'http://www.docsafe.com.br',
    'contributors': [
        'Alexandre Defendi <alexandre_defendi@hotmail.com>',
    ],
    'depends': [
        'br_cnab'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/cnab_retorno_views.xml',
        'views/cnab_retorno_line_views.xml',
    ],
    'installable': True
}