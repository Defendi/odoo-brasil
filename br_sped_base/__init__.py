import logging
import os
import csv

from . import models

_logger = logging.getLogger(__name__)

def post_init(cr, registry):
    _logger.info('<<< Importando UOM')
#     from odoo.tools import convert_file

    import odoo
    import odoo.modules as addons
    from odoo import SUPERUSER_ID
    from odoo.tools.misc import file_open
    from odoo.tools import config, convert_file

    try:
        filename = 'data/product.uom.csv'
        convert_file(cr, 'br_sped_base', filename, None, mode='init', noupdate=True, kind='init', report=None)
        return
    except:
        pass

    
    rtp = os.path.normcase(os.path.abspath(config['root_path']))
    adps = addons.module.ad_paths

    # Busca o arquivo nos paths
    file_name = 'br_sped_base/data/product.uom.csv'
    file_path = False
    for root in adps + [rtp]:
        efile_name = str(root+'/'+file_name)
        if os.path.exists(efile_name):
            file_path = efile_name
            break
    
    if not file_path:
        return True
 
 
    context = {}
    env = odoo.api.Environment(cr, SUPERUSER_ID, context)

    model = env['product.uom']
    irmodeldata = env['ir.model.data']
    
    with open(file_path) as csv_file:
        _logger.info('Abriu o arquivo')
        csv_reader = csv.reader(csv_file,delimiter=',')
        _logger.info('Tratou o arquivo')
        col_names = []
        for sidx, row in enumerate(csv_reader):
            vals = {}
            _logger.info('>>> Linha %s - %s' % (str(sidx),str(col_names)))
            if sidx == 0:
                for col in row:
                    col_names.append(col)
                _logger.info('>>> Colunas %s' % str(col_names))
            else:
                for idx, col in enumerate(row):
                    vals[col_names[idx]] = col
                id_name = vals['id'].split('.')
                id_categ = vals['category_id/id'].split('.')
                _logger.info('>>> Valores %s' % str(vals))
                _logger.info('>>> Categoria ID %s' % str(id_categ))
                imd = irmodeldata.search([('module','=',id_name[0]),('name','ilike',id_name[1])])
                ctg = irmodeldata.search([('module','=',id_categ[0]),('name','ilike',id_categ[1])])
                vals['category_id'] = ctg.res_id
                _logger.info('>>> Achou Categoria ID %s(%s)' % (str(ctg.name),str(ctg.id)))
                if len(imd) > 0:
                    _logger.info('>>> Achou o registro %s(%s)' % (str(imd.name),str(imd.res_id)))
                    model = model.search([('id','=',imd.res_id)],limit=1)
                    if len(model) > 0:
                        _logger.info('>>> Alterando o valor %s %s' % (str(vals['name']),str(vals['l10n_br_description'])))
                        model.name = vals['name']
                        model.l10n_br_description = vals['l10n_br_description']
                    else:
                        _logger.info('>>> Não abriu o ID')
                        _logger.info('>>> Criar novo registro')
                        model.create(vals)
                else:
                    _logger.info('>>> Criar novo registro')
                    model.create(vals)
