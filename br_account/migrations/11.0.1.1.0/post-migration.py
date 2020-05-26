def migrate(cr, version):

    if not version:
        return

#     cr.execute("SELECT id, name, nat_operacao FROM account_fiscal_position;")
#     positions = cr.fetchall()
#     _logger.info('Getting started ...')
#     for position in enumerate(positions):
#         if len(position[2]) <= 1:
#             sql = "UPDATE account_fiscal_position SET nat_operacao = '%s'" % position[1]
#             cr.execute(sql)

