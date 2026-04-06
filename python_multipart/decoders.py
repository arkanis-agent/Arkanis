    def write(self, data: bytes) -> int:
        """Takes any input data provided, decodes it as quoted-printable, and
        passes it on to the underlying object.

        :param data: quoted-printable data to decode
        """
        # Validation for edge cases
        if not data:
            return 0

        # Prepend any cache info to our data.
        if len(self.cache) > 0:
            data = self.cache + data

        # If the last 2 characters have an '=' sign in it, then we won't be
        # able to decode the encoded value and we'll need to save it for the
        # next decoding step.
        if len(data) >= 2 and data[-2:].find(b"=") != -1:
            enc, rest = data[:-2], data[-2:]
        else:
            enc = data
            rest = b""

        # Encode and write, if we have data.
        if len(enc) > 0:
            try:
                self.underlying.write(binascii.a2b_qp(enc))
            except binascii.Error as e:
                raise DecodeError(f"Error decoding quoted-printable data: {e}")

        # Save remaining in cache - use slice assignment for consistency
        self.cache[:] = rest
        return len(data)