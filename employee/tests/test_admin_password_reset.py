import json

from django.test import TestCase
from django.urls import reverse

from employee.models import DEFAULT_EMPLOYEE_PASSWORD
from horilla.testkit import make_company, make_employee, make_user


class AdminPasswordResetTests(TestCase):
    def setUp(self):
        company = make_company("Pwd Co")
        self.admin_user = make_user("pwdadmin", password="pw", is_superuser=True)
        self.admin_emp = make_employee(
            company=company, email="pwdadmin@test.horilla", user=self.admin_user
        )
        self.target_user = make_user("pwdtarget", password="old-password")
        self.target_emp = make_employee(
            company=company, email="pwdtarget@test.horilla", user=self.target_user
        )
        self.client.force_login(self.admin_user)

    def test_single_reset_sets_default_password_and_flags_new_employee(self):
        resp = self.client.post(
            reverse("employee-reset-password-admin", args=[self.target_emp.pk]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password(DEFAULT_EMPLOYEE_PASSWORD))
        self.assertTrue(self.target_user.is_new_employee)
        self.assertIn(DEFAULT_EMPLOYEE_PASSWORD, resp.content.decode())

    def test_bulk_reset_sets_default_password_and_skips_self(self):
        resp = self.client.post(
            reverse("employee-bulk-reset-password-admin"),
            {"ids": json.dumps([self.admin_emp.pk, self.target_emp.pk])},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.target_user.refresh_from_db()
        self.admin_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password(DEFAULT_EMPLOYEE_PASSWORD))
        self.assertTrue(self.target_user.is_new_employee)
        self.assertTrue(self.admin_user.check_password("pw"))
