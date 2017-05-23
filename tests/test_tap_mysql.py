import unittest
import pymysql
import tap_mysql


class TestTypeMapping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with pymysql.connect(
            host='localhost',
            user='root',
            password='password') as con:
            try:
                con.execute('DROP DATABASE tap_mysql_test')
            except:
                pass
            con.execute('CREATE DATABASE tap_mysql_test')

        con = pymysql.connect(
            host='localhost',
            user='root',
            password='password',
            database='tap_mysql_test')

        with con.cursor() as cur:
            cur.execute('''
            CREATE TABLE column_test (
            c_pk INTEGER PRIMARY KEY,
            c_decimal DECIMAL,
            c_decimal_2 DECIMAL(11, 2),
            c_tinyint TINYINT,
            c_smallint SMALLINT,
            c_mediumint MEDIUMINT,
            c_int INT,
            c_bigint BIGINT,
            c_float FLOAT,
            c_double DOUBLE,
            c_bit BIT(4)
            )''')

            discovered = tap_mysql.discover_schemas(con)
        
            cls.schema = discovered['column_test']['schema']
            
            
    def test_decimal(self):
        self.assertEqual(self.schema['properties']['c_decimal'], {
            'type': 'number',
            'inclusion': 'available',
            'exclusiveMaximum': 10000000000,
            'multipleOf': 1
        })

    def test_decimal_with_defined_scale_and_precision(self):        
        self.assertEqual(self.schema['properties']['c_decimal_2'], {
            'type': 'number',
            'inclusion': 'available',
            'exclusiveMaximum': 1000000000,
            'multipleOf': 0.01})

    def test_tinyint(self):
        self.assertEqual(self.schema['properties']['c_tinyint'], {
            'type': 'integer',
            'inclusion': 'available',
            'minimum': -128,
            'maximum': 127
        })

    def test_smallint(self):
        self.assertEqual(self.schema['properties']['c_smallint'], {
            'type': 'integer',
            'inclusion': 'available',
            'minimum': -32768,
            'maximum':  32767
        })

    def test_mediumint(self):
        self.assertEqual(self.schema['properties']['c_mediumint'], {
            'type': 'integer',
            'inclusion': 'available',
            'minimum': -8388608,
            'maximum':  8388607
        })

    def test_int(self):
        self.assertEqual(self.schema['properties']['c_int'], {
            'type': 'integer',
            'inclusion': 'available',
            'minimum': -2147483648,
            'maximum': 2147483647
        })
        
    def test_bigint(self):
        self.assertEqual(self.schema['properties']['c_bigint'], {
            'type': 'integer',
            'inclusion': 'available',
            'minimum': -9223372036854775808,
            'maximum':  9223372036854775807
        })

    def test_float(self):
        self.assertEqual(self.schema['properties']['c_float'], {
            'type': 'number',
            'inclusion': 'available',
        })                        
    

    def test_double(self):
        self.assertEqual(self.schema['properties']['c_double'], {
            'type': 'number',
            'inclusion': 'available',
        })                        
    
    def test_bit(self):
        self.assertEqual(self.schema['properties']['c_bit'], {
            'inclusion': 'unsupported',
            'description': 'Unsupported column type bit(4)',
        })                        

    def test_pk(self):
        self.assertEqual(
            self.schema['properties']['c_pk']['inclusion'],
            'automatic')