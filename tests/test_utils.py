from common.utils import clean_html, is_company_email, is_junk_company_name, make_uid, safe_console


class TestMakeUid:
    def test_basic(self):
        uid = make_uid("Python Developer", "TechCorp", "Kerala")
        assert isinstance(uid, str)
        assert len(uid) == 32  # MD5 hex length

    def test_deterministic(self):
        uid1 = make_uid("Python Developer", "TechCorp", "Kerala")
        uid2 = make_uid("Python Developer", "TechCorp", "Kerala")
        assert uid1 == uid2

    def test_case_insensitive(self):
        uid1 = make_uid("Python Developer", "TechCorp", "Kerala")
        uid2 = make_uid("python developer", "techcorp", "kerala")
        assert uid1 == uid2

    def test_different_inputs_different_uids(self):
        uid1 = make_uid("Python Developer", "TechCorp")
        uid2 = make_uid("Java Developer", "TechCorp")
        assert uid1 != uid2

    def test_empty_location(self):
        uid = make_uid("Python Developer", "TechCorp")
        assert isinstance(uid, str)


class TestIsCompanyEmail:
    def test_valid_company_email(self):
        valid, reason = is_company_email("hr@techcorp.com")
        assert valid is True
        assert reason == "valid"

    def test_empty_email(self):
        valid, reason = is_company_email("")
        assert valid is False

    def test_none_email(self):
        valid, reason = is_company_email(None)
        assert valid is False

    def test_invalid_format(self):
        valid, reason = is_company_email("not-an-email")
        assert valid is False

    def test_junk_domain(self):
        valid, reason = is_company_email("user@sentry.io")
        assert valid is False
        assert "junk" in reason

    def test_spam_domain(self):
        valid, reason = is_company_email("user@linkedin.com")
        assert valid is False
        assert "job board" in reason

    def test_scammer_like_email(self):
        valid, reason = is_company_email("hr@google.com")
        assert valid is False

    def test_feed_placeholder_email(self):
        valid, reason = is_company_email("your.email@domain.com")
        assert valid is False
        assert reason == "placeholder"

    def test_feed_placeholder_variants(self):
        for email in (
            "yourname@domain.com",
            "youremail@yourcompany.com",
            "your_name@yourdomain.com",
            "your-email@domain.com",
            "yourcontact@somecompany.com",
        ):
            valid, reason = is_company_email(email)
            assert valid is False, email
            assert reason == "placeholder", email

    def test_placeholder_domain_still_rejected(self):
        valid, reason = is_company_email("recruiter@domain.com")
        assert valid is False
        assert "junk" in reason


class TestIsJunkCompanyName:
    def test_tagline_company_names_flagged(self):
        for name in (
            "Building India's first AI-powered recruitment marketplace",
            "Building enterprise data, cloud, and AI solutions.",
            "A leading AI and digital transformation consulting firm.",
            "a leading provider of electronic trading solutions in India.",
            "Hiring for Service Based Company",
            "Global Digital Transformation Solutions Provider",
            "We are a fast-growing AI startup.",
        ):
            assert is_junk_company_name(name) is True, name

    def test_real_company_names_not_flagged(self):
        for name in (
            "TechCorp",
            "Games24x7",
            "Prophaze Technologies (P) Ltd",
            "Tata Consultancy Services",
            "Selkirk Sport - We Are Pickleball",
            "Interdisciplinary Transformation University (IT:U)",
            "L'Agence Pour Le Non-Marchand",
            "Cascade Revenue Management - An AIMA Group Company",
            "",
            None,
        ):
            assert is_junk_company_name(name) is False, name


class TestCleanHtml:
    def test_strip_tags(self):
        assert clean_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_empty_input(self):
        assert clean_html("") == ""
        assert clean_html(None) == ""

    def test_normalize_whitespace(self):
        assert clean_html("Hello    World") == "Hello World"


class TestSafeConsole:
    def test_normal_text(self):
        assert safe_console("Hello") == "Hello"

    def test_unicode(self):
        result = safe_console("Hello 世界")
        assert isinstance(result, str)
