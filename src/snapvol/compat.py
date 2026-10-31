import codecs

from snapcast.control.protocol import SnapcastProtocol

_orig_data_received = SnapcastProtocol.data_received


def _data_received(self, data):
    decoder = self.__dict__.setdefault(
        "_utf8_decoder", codecs.getincrementaldecoder("utf-8")()
    )
    text = decoder.decode(data)
    if text:
        _orig_data_received(self, text.encode())


SnapcastProtocol.data_received = _data_received
