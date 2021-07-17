from odoo import api, fields, models, _
from odoo.exceptions import UserError
import pandas as pd
from mlxtend.frequent_patterns import apriori
from mlxtend.frequent_patterns import association_rules
import csv
import base64
from io import StringIO

import logging
_logger = logging.getLogger(__name__)

def encode_units(x):
    if x <= 0:
        return 0
    if x >= 1:
        return 1

class MarketBasketAnalysis(models.TransientModel):
    _name = 'market.basket.analysis'
    _description = 'Market Basket Analysis'

    name = fields.Char(help="the name of csv/excel file", default=lambda self: self.env.user.company_id.name)
    start_date = fields.Datetime(help="Filtering Sale Order from Specific Date")
    end_date = fields.Datetime(help="Filtering Sale Order to Specific Date")
    data_type = fields.Selection([
        ('items', 'Items'),
        ('categories', 'Categories')],
        default="items"
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    minimum_support = fields.Float(default=0.01)
    lift = fields.Float(default=0.01)
    confidence = fields.Float(default=0.01)
    file_import = fields.Binary(string="File ( .csv )")

    def get_sales_data(self):
        # get categories of each item in sale orders
        query = """
            select 
                so.name sale_number,
                {} as description,
                sol.product_uom_qty as quantity,
                rc.name as warehouse
            from sale_order_line sol
            join res_company rc on sol.company_id = rc.id
            join sale_order so on sol.order_id = so.id
            join product_product pp on sol.product_id = pp.id
            join product_template pt on pp.product_tmpl_id = pt.id
            join product_category pc on pt.categ_id = pc.id
            where sol.company_id = %s
            and sol.create_date BETWEEN %s AND %s 
            order by so.name, so.partner_id
        """.format('pt.name' if self.data_type == 'items' else 'pc.name')
        params = (
            self.company_id.id,
            self.start_date,
            self.end_date
        )
        self._cr_read.execute(query, params)
        sales = self._cr_read.dictfetchall()
        return sales
        
    def action_create_mba_excel(self):
        if self.minimum_support <= 0:
            raise UserError(_('Minimum support cannot bellow/even zero'))
        
        # Read Data Sales 
        query_get_sales = self.get_sales_data()
        df = pd.DataFrame(query_get_sales)
        df.head()
        _logger.info("Read Data: %s" % (df))

        # Clean up data:
            # - spaces on description(SKU/Item) 
            # - rows with empty sale_number
        df['description'] = df['description'].str.strip()
        df.dropna(axis=0, subset=['sale_number'], inplace=True)
        _logger.info("Clean up data: %s" % (df))

        # Get list warehouse
        warehouses = set(df['warehouse'])
        _logger.info("list warehouse: %s" % (warehouses))

        for wh in warehouses:
            # Consolidate the items into 1 transaction per row with each product
            basket = (df[df['warehouse'] == wh]
                    .groupby(['sale_number', 'description'])['quantity']
                    .sum().unstack().reset_index().fillna(0)
                    .set_index('sale_number'))
            basket.head()
            _logger.info("Consolidate the items into 1 transaction per row with each product: %s" % (basket))

            # The frequent items using apriori then build the rules with association_rules
            basket_sets = basket.applymap(encode_units)
            frequent_itemsets = apriori(basket_sets, min_support=self.minimum_support, use_colnames=True)
            rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
            _logger.info("The frequent items using apriori then build the rules with association_rules: %s" % (rules))
            # filter the dataframe using standard pandas code (example: lift(6) & confidence(8))
            rules = rules[(rules['lift'] >= self.lift) &
                    (rules['confidence'] >= self.confidence)]
            _logger.info("filter the dataframe using standard pandas code")
            rules.head()
            list_values = rules.values.tolist()

            # add name to file csv/excel
            filename = "%s.csv" % (self.name)
            csvfile = StringIO()
            csvwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
            
            # insert data Market Basket Analysis to CSV
            csvwriter.writerow(h for h in rules)
            for vals in list_values:
                csvwriter.writerow(val for val in vals)
            csv_file = csvfile.getvalue()
            csvfile.close()
            statement_id = self.create({
                'file_import': base64.encodestring(csv_file.encode('utf-8')),
                'name': filename,
            })

            # download File CSV
            action = {
                'name': 'Download CSV',
                'type': 'ir.actions.act_url',
                'url': "web/content/market.basket.analysis/{}/file_import/{}?download=true".format(statement_id.id, statement_id.name),
                'target': 'download',
                }
            return action