"""Company isolation via HorillaCompanyManager + selected-company context."""

from datetime import date, timedelta

from django.test import TestCase

from base.models import Holidays
from horilla.testkit import CompanyFilterTestMixin, make_company


class HolidayCompanyIsolationTests(CompanyFilterTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = make_company("Company A")
        cls.company_b = make_company(
            "Company B",
            address="2 Other St",
            city="SF",
            zip="94105",
        )
        day_a = date.today() - timedelta(days=40)
        day_b = date.today() - timedelta(days=20)
        cls.holiday_a = Holidays.objects.create(
            name="Holiday A",
            start_date=day_a,
            end_date=day_a,
            company_id=cls.company_a,
        )
        cls.holiday_b = Holidays.objects.create(
            name="Holiday B",
            start_date=day_b,
            end_date=day_b,
            company_id=cls.company_b,
        )

    def test_company_a_sees_only_own_holidays(self):
        self.set_company_context(self.company_a.pk)
        visible = list(Holidays.objects.all())
        self.assertIn(self.holiday_a, visible)
        self.assertNotIn(self.holiday_b, visible)

    def test_company_b_sees_only_own_holidays(self):
        self.set_company_context(self.company_b.pk)
        visible = list(Holidays.objects.all())
        self.assertNotIn(self.holiday_a, visible)
        self.assertIn(self.holiday_b, visible)

    def test_entire_bypasses_company_filter(self):
        self.set_company_context(self.company_a.pk)
        all_rows = list(Holidays.objects.entire())
        self.assertIn(self.holiday_a, all_rows)
        self.assertIn(self.holiday_b, all_rows)

    def test_no_company_context_returns_unfiltered(self):
        self.clear_company_context()
        all_rows = list(Holidays.objects.all())
        self.assertIn(self.holiday_a, all_rows)
        self.assertIn(self.holiday_b, all_rows)

    def test_empty_allowed_ids_hides_company_rows_but_keeps_unscoped_rows(self):
        from types import SimpleNamespace
        from horilla.horilla_middlewares import _thread_locals

        unscoped = Holidays.objects.create(
            name="Shared Holiday",
            start_date=date.today(),
            end_date=date.today(),
            company_id=None,
        )
        prev_req = getattr(_thread_locals, "request", None)
        self.set_company_context("all")
        _thread_locals.request = SimpleNamespace(
            GET={}, all_my_company_ids=[], allowed_company_ids=[]
        )
        try:
            visible = list(Holidays.objects.all())
        finally:
            _thread_locals.request = prev_req
            self.clear_company_context()
        self.assertIn(unscoped, visible)
        self.assertNotIn(self.holiday_a, visible)
        self.assertNotIn(self.holiday_b, visible)

    def test_unscoped_employee_sees_self_in_attendance_request_when_no_company(self):
        from django.test import override_settings
        from django.urls import reverse
        from base.models import EmployeeShift
        from horilla.testkit import make_user
        from employee.models import Employee

        EmployeeShift.objects.create(employee_shift="Morning Shift")
        user = make_user("unscoped_emp", password="pw")
        emp = Employee.objects.create(
            employee_first_name="Hanley",
            employee_last_name="Test",
            email="hanley_unscoped@test.horilla",
            phone="9999999999",
            employee_user_id=user,
        )
        self.client.force_login(user)
        with override_settings(COMPANY_SCOPED_PERMISSIONS=True):
            r_new = self.client.get(
                reverse("request-new-attendance"), HTTP_HX_REQUEST="true"
            )
            r_bulk = self.client.get(
                reverse("request-bulk-attendance"), HTTP_HX_REQUEST="true"
            )
        self.assertEqual(r_new.status_code, 200)
        self.assertIn(f'name="employee_id" value="{emp.pk}"', r_new.content.decode())
        self.assertIn("Morning Shift", r_new.content.decode())
        self.assertEqual(r_bulk.status_code, 200)
        self.assertIn(f'name="employee_id" value="{emp.pk}"', r_bulk.content.decode())
        self.assertIn("Morning Shift", r_bulk.content.decode())

        from django.contrib.auth.models import Permission

        hr_user = make_user("unscoped_hr", password="pw")
        hr_user.user_permissions.add(
            Permission.objects.get(
                codename="add_attendance", content_type__app_label="attendance"
            ),
            Permission.objects.get(
                codename="change_attendance", content_type__app_label="attendance"
            ),
            Permission.objects.get(
                codename="add_feedback", content_type__app_label="pms"
            ),
        )
        Employee.objects.create(
            employee_first_name="HRViewer",
            employee_last_name="Test",
            email="hr_unscoped@test.horilla",
            phone="8888888888",
            employee_user_id=hr_user,
        )
        self.client.force_login(hr_user)
        with override_settings(COMPANY_SCOPED_PERMISSIONS=True):
            hr_new = self.client.get(
                reverse("request-new-attendance"), HTTP_HX_REQUEST="true"
            )
            hr_bulk = self.client.get(
                reverse("request-bulk-attendance"), HTTP_HX_REQUEST="true"
            )
        self.assertEqual(hr_new.status_code, 200)
        self.assertIn("Hanley", hr_new.content.decode())
        self.assertIn("Morning Shift", hr_new.content.decode())
        self.assertEqual(hr_bulk.status_code, 200)
        self.assertIn("Hanley", hr_bulk.content.decode())
        self.assertIn("Morning Shift", hr_bulk.content.decode())
