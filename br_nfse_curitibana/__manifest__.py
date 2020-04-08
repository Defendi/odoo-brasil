# © 2020 Alexandre Defendi

{  # pylint: disable=C8101,C8103
    'name': 'Integração Nota Curitibana - ',
    'description': """Efetua a integração com a prefeitura de Curitiba
        - Mantido por Defendi""",
    'summary': """Efetua a integração com a prefeitura de Curitiba
    - Mantido por Defendi""",
    'version': '11.0.0.1',
    'category': "Accounting & Finance",
    'author': 'Defendi',
    'license': 'AGPL-3',
    'website': '',
    'contributors': [
    ],
    'depends': [
        'br_nfse',
    ],
    'data': [
        'data/br_account.fiscal.document.csv',
        'data/br_account_document_serie.xml',
    ],
    'application': True,
}
