from mock import patch
from converter import ORMConverter
import pickle

@patch("converter.ORMConverter")
def test_query_griebnitzsee(mock_converter):
    query_data = None
    with open("tests/mock_data/griebnitzsee_req.txt","rb") as f:
        query_data = pickle.load(f)
    if not query_data:
        raise Exception("Test could not be run, since data was not loaded correctly")
    mock_converter()._get_track_objects.return_value = query_data
    converter = ORMConverter()
    res = converter.run(x1=52.39503, y1=13.12242, x2=52.3933, y2=13.1421)
    assert 'node' in res
    assert 'edge' in res