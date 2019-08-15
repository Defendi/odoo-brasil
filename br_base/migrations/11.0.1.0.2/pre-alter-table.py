
# from openupgradelib.openupgrade import rename_tables, rename_columns


def migrate(cr, version):
    sql = '''
UPDATE res_partner 
    SET display_name = case 
        when legal_name is not null and legal_name <> '' then 
            CONCAT('[',name,'] ',legal_name) 
        else name 
        end
     WHERE is_company = true; '''
    cr.execute(sql)
