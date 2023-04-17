import pickle

from mock import patch

from orm_importer.importer import ORMImporter


@patch("orm_importer.importer.ORMImporter")
def test_query_griebnitzsee(mock_converter):
    query_data = None
    with open("tests/mock_data/griebnitzsee_req.txt", "rb") as f:
        query_data = pickle.load(f)
    if not query_data:
        raise Exception("Test could not be run, since data was not loaded correctly")
    mock_converter()._get_track_objects.return_value = query_data
    converter = ORMImporter()
    res = converter.run(
        "52.394471570989126 13.12194585800171 52.3955583542288 13.133854866027834 52.39436681938324 13.134176731109621 52.39326691251008 13.122761249542238"
    )

    assert len(res.nodes) == 10
    assert len(res.edges) == 9
    assert len(res.signals) == 14
