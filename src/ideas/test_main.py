import unittest
from unittest.mock import MagicMock

from unittest.mock import Mock, patch
from datetime import datetime, time
from main import scale_sql_database

class TestScaleSqlDatabase(unittest.TestCase):
    @patch('main.sql_client')
    @patch('main.datetime')
    def test_no_change_in_dtu(self, mock_datetime, mock_sql_client):
        database = Mock()
        database.current_service_objective_name = 'DTU'
        tiers = [{'name': 'DTU', 'peak_dtu': 'DTU'}]
        result = scale_sql_database(database, tiers)
        self.assertEqual(result, ('No Change', 'Current DTU is already optimal.'))

    @patch('main.sql_client')
    @patch('main.datetime')
    def test_no_matching_tier(self, mock_datetime, mock_sql_client):
        database = Mock()
        database.current_service_objective_name = 'DTU'
        tiers = [{'name': 'OtherDTU', 'peak_dtu': 'DTU'}]
        result = scale_sql_database(database, tiers)
        self.assertEqual(result, ('Failed', 'No matching tier found for the current DTU.'))

    @patch('main.sql_client')
    @patch('main.datetime')
    def test_off_peak_hours(self, mock_datetime, mock_sql_client):
        database = Mock(spec=dict)
        database.configure_mock(**{'current_service_objective_name': 'DTU', 'id': '/some/path/to/database/with/extra/segments', 'name': 'mock_database'})        
        tiers = [{'name': 'DTU', 'peak_dtu': 'PeakDTU', 'off_peak_dtu': 'OffPeakDTU', 'off_peak_start': '00:00', 'off_peak_end': '23:59'}]
        mock_time = MagicMock()
        mock_time.__le__ = MagicMock(return_value=True)
        mock_time.__ge__ = MagicMock(return_value=True)
        mock_datetime.now.return_value.time.return_value = mock_time
        result = scale_sql_database(database, tiers)
        self.assertEqual(result, ('Success', 'DTU scaled to OffPeakDTU.'))

    @patch('main.sql_client')
    @patch('main.datetime')
    def test_peak_hours(self, mock_datetime, mock_sql_client):
        database = Mock(spec=dict)
        database.configure_mock(**{'current_service_objective_name': 'DTU', 'id': '/some/path/to/database/with/extra/segments', 'name': 'mock_database'})   
        tiers = [{'name': 'DTU', 'peak_dtu': 'PeakDTU', 'off_peak_dtu': 'OffPeakDTU', 'off_peak_start': '00:00', 'off_peak_end': '01:00'}]
        mock_time = MagicMock()
        mock_time.__le__ = MagicMock(return_value=False)
        mock_time.__ge__ = MagicMock(return_value=False)
        mock_datetime.now.return_value.time.return_value = mock_time
        result = scale_sql_database(database, tiers)
        self.assertEqual(result, ('Success', 'DTU scaled to PeakDTU.'))

    @patch('main.sql_client')
    @patch('main.datetime')
    def test_exception(self, mock_datetime, mock_sql_client):
        database = Mock()
        database.current_service_objective_name = 'DTU'
        tiers = [{'name': 'DTU', 'peak_dtu': 'PeakDTU'}]
        mock_sql_client.databases.begin_update.side_effect = Exception('Error')
        result = scale_sql_database(database, tiers)
        self.assertEqual(result[0], 'Failed')

if __name__ == '__main__':
    unittest.main()