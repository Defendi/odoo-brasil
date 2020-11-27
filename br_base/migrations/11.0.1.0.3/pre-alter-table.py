
# from openupgradelib.openupgrade import rename_tables, rename_columns


def migrate(cr, version):
    sql = '''UPDATE res_partner 
    SET display_name = case 
        when legal_name is not null and legal_name <> '' then 
            CONCAT('[',name,'], ',legal_name) 
        else name 
        end
     WHERE is_company = true AND parent_id IS NULL; '''
    cr.execute(sql)

    sql = '''UPDATE res_partner 
    SET display_name = name
     WHERE is_company = false AND parent_id IS NULL; '''
    cr.execute(sql)

    sql = '''UPDATE res_partner AS p1
    SET display_name = CONCAT(p2.name,', ',p1.name)
    FROM res_partner AS p2
    WHERE p2.id = p1.parent_id AND p1.is_company = false;'''
    cr.execute(sql)

    sql = '''UPDATE res_partner AS p1
    SET display_name = CONCAT(p2.name,', Filial ',p1.name)
    FROM res_partner AS p2
    WHERE p2.id = p1.parent_id AND p1.is_company = true;'''
    cr.execute(sql)
