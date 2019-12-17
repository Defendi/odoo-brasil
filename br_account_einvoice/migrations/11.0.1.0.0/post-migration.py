

def migrate(cr, version):
    # Alter table name
#     if not version:
#         return

    cr.execute("UPDATE res_company SET tipo_ambiente_nfse = 'producao' WHERE tipo_ambiente_nfse = '1';")
    cr.execute("UPDATE res_company SET tipo_ambiente_nfse = 'homologacao' WHERE tipo_ambiente_nfse = '2';")
