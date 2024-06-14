from faker import Faker
import uuid
import time
import datetime

class Fake():
    def __init__(self):
        self._faker = Faker()

    def _discriminator(self):
        return self._faker.hexify('^^^^^^^^')

    def guid(self):
        return str(uuid.uuid4())

    def email(self):
        return f'{self._faker.first_name()}.{self._faker.last_name()}_{self._discriminator()}@{self._faker.domain_name(1)}'

    def timestamp_iso(self):
        return self._faker.iso8601()

    def timestamp_unix(self):
        return self._faker.unix_time()

    def timestamp_current_iso(self):
        return datetime.datetime.utcnow().isoformat()

    def timestamp_current_unix(self):
        return time.time()

    def ip(self):
        return self.ipv4()

    def ipv4(self):
        return self._faker.ipv4()

    def ipv6(self):
        return self._faker.ipv6()

    def domain(self):
        return self._faker.domain_name(2)

    def username(self):
        return self._faker.user_name() + self._discriminator()

    def password(self):
        return self._faker.password()

    def first_name(self):
        return self._faker.first_name()

    def last_name(self):
        return self._faker.last_name()

    def country_code(self):
        return self._faker.country_code()

    def street_address(self):
        return self._faker.street_address()

    def zip_code(self):
        return self._faker.random_uppercase_letter() \
            + str(self._faker.random_number(1)) \
            + self._faker.random_uppercase_letter() \
            + " " \
            + str(self._faker.random_number(1)) \
            + self._faker.random_uppercase_letter() \
            + str(self._faker.random_number(1))

    def city(self):
        return self._faker.city()

    def word(self):
        return self._faker.word()

    def credit_card_number(self):
        return self._faker.credit_card_number()
    def credit_card_expire(self):
        return self._faker.credit_card_expire()
    def credit_card_security_code(self):
        return self._faker.credit_card_security_code()
    def credit_card_provider(self):
        return self._faker.credit_card_provider()

    def int(self):
        return self._faker.random_number()

    def small_int(self):
        return self._faker.random_number(2)

    def float(self):
        return self._faker.random_number() / 1000

    def small_float(self):
        return self._faker.random_number(4) / 100

    def zip_code_us(self):
        return self._faker.zipcode()

    def phone_number(self):
        return self._faker.phone_number()
