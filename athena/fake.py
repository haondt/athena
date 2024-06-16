from faker import Faker
import uuid
import time
import datetime

class Fake():
    """Generate randomized fake data"""
    def __init__(self):
        self._faker = Faker()

    def _discriminator(self):
        return self._faker.hexify('^^^^^^^^')

    def guid(self):
        """Random guid."""
        return str(uuid.uuid4())

    def email(self):
        """Random email."""
        return f'{self._faker.first_name()}.{self._faker.last_name()}_{self._discriminator()}@{self._faker.domain_name(1)}'

    def timestamp_iso(self):
        """Random iso8601 timestamp."""
        return self._faker.iso8601()

    def timestamp_unix(self):
        """Random unix (posix) timestamp."""
        return self._faker.unix_time()

    def timestamp_current_iso(self):
        """Current time in iso8601 format"""
        return datetime.datetime.utcnow().isoformat()

    def timestamp_current_unix(self):
        """Current time in unix (posix) format."""
        return time.time()

    def ip(self):
        """Random ipv4 address."""
        return self.ipv4()

    def ipv4(self):
        """Random ipv4 address."""
        return self._faker.ipv4()

    def ipv6(self):
        """Random ipv6 address."""
        return self._faker.ipv6()

    def domain(self):
        """Random domain name."""
        return self._faker.domain_name(2)

    def username(self):
        """Random username."""
        return self._faker.user_name() + self._discriminator()

    def password(self):
        """Random password."""
        return self._faker.password()

    def first_name(self):
        "Random first name."
        return self._faker.first_name()

    def last_name(self):
        """Random last name."""
        return self._faker.last_name()

    def country_code(self):
        """Random country code."""
        return self._faker.country_code()

    def street_address(self):
        """Random street address."""
        return self._faker.street_address()

    def zip_code(self):
        """Random (Canadian) zip code."""
        return self._faker.random_uppercase_letter() \
            + str(self._faker.random_number(1)) \
            + self._faker.random_uppercase_letter() \
            + " " \
            + str(self._faker.random_number(1)) \
            + self._faker.random_uppercase_letter() \
            + str(self._faker.random_number(1))

    def city(self):
        """Random city."""
        return self._faker.city()

    def word(self):
        """Random word."""
        return self._faker.word()

    def credit_card_number(self):
        """Random credit card number."""
        return self._faker.credit_card_number()
    def credit_card_expire(self):
        """Random credit card expiry (mm/yy)."""
        return self._faker.credit_card_expire()
    def credit_card_security_code(self):
        """Random credit card security code."""
        return self._faker.credit_card_security_code()
    def credit_card_provider(self):
        """Random credit card provider."""
        return self._faker.credit_card_provider()

    def int(self):
        """Random integer."""
        return self._faker.random_number()

    def small_int(self):
        """Random 2 digit integer."""
        return self._faker.random_number(2)

    def float(self):
        """Random floating point number."""
        return self._faker.random_number() / 1000

    def small_float(self):
        """Random 4 digit floating point number (00.00 - 99.99)."""
        return self._faker.random_number(4) / 100

    def zip_code_us(self):
        """Random (US) zip code."""
        return self._faker.zipcode()

    def phone_number(self):
        """Random phone number"""
        return self._faker.phone_number()
