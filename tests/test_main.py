import xplitpay
from xplitpay.export import generate_markdown

class TestMain:
    def test_parse_xplit(self):
        xplitlog = xplitpay.parse_xplit("tests/2_ppl.xplit", SUPPORT_48_HOURS=True, ALWAYS_INVOLVE_EVERYONE=True)
        assert xplitlog

    def test_generate_markdown(self):
        xplitlog = xplitpay.parse_xplit("tests/2_ppl.xplit", SUPPORT_48_HOURS=True, ALWAYS_INVOLVE_EVERYONE=True)
        generate_markdown(xplitlog, "test.md", locale="en")
        assert True