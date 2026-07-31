from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from chore_app import models, forms, views


def mk(role, name, pts=0):
    u = models.User.objects.create_user(username=name, password='pw123456!x')
    u.role = role; u.points_balance = Decimal(pts); u.save()
    return u


class Flow(TestCase):
    def setUp(self):
        self.parent = mk('Parent', 'mum')
        self.kid = mk('Child', 'kid', 100)
        self.kid2 = mk('Child', 'kid2', 100)
        self.pc, self.cc, self.c2 = Client(), Client(), Client()
        self.pc.force_login(self.parent); self.cc.force_login(self.kid); self.c2.force_login(self.kid2)

    def test_early_bonus_claim_no_crash(self):
        ch = models.Chore.objects.create(name='Dishes', points=Decimal('10'),
                                         early_bonus=True, bonus_end_time=23)
        r = self.cc.post(reverse('claim_chore', args=[ch.pk]))
        self.assertEqual(r.status_code, 302)
        cl = models.ChoreClaim.objects.get(user=self.kid)
        now_h = views.timezone.localtime().hour
        expected = Decimal('12.50') if 5 <= now_h < 23 else Decimal('10')
        self.assertEqual(cl.points, expected)

    def test_child_cannot_return_other_childs_claim(self):
        ch = models.Chore.objects.create(name='Bins', points=Decimal('5'))
        self.cc.post(reverse('claim_chore', args=[ch.pk]))
        cl = models.ChoreClaim.objects.get(user=self.kid)
        self.c2.post(reverse('return_chore', args=[cl.pk]))
        self.assertTrue(models.ChoreClaim.objects.filter(pk=cl.pk).exists())
        self.cc.post(reverse('return_chore', args=[cl.pk]))
        self.assertFalse(models.ChoreClaim.objects.filter(pk=cl.pk).exists())

    def test_no_duplicate_chores_when_multi_assigned(self):
        ch = models.Chore.objects.create(name='Multi', points=Decimal('5'))
        ch.assigned_children.set([self.kid, self.kid2])
        r = self.cc.get(reverse('child_profile'))
        self.assertEqual(len([c for c in r.context['chores'] if c.pk == ch.pk]), 1)

    def test_daily_message_renders(self):
        models.Text.objects.create(key='daily_message', text='Be excellent', enabled=True)
        r = self.cc.get(reverse('child_profile'))
        self.assertContains(r, 'Be excellent')

    def test_zero_point_claim_cannot_be_approved(self):
        ch = models.Chore.objects.create(name='Free', points=Decimal('0'))
        cl = models.ChoreClaim.objects.create(chore=ch, user=self.kid, chore_name='Free',
                                              points=Decimal('0'))
        self.pc.post(reverse('approve_chore_claim', args=[cl.pk]))
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points_balance, Decimal('100'))

    def test_approve_awards_once(self):
        ch = models.Chore.objects.create(name='Vacuum', points=Decimal('7'))
        self.cc.post(reverse('claim_chore', args=[ch.pk]))
        cl = models.ChoreClaim.objects.get(user=self.kid)
        self.pc.post(reverse('approve_chore_claim', args=[cl.pk]))
        self.pc.post(reverse('approve_chore_claim', args=[cl.pk]))
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points_balance, Decimal('107'))

    def test_point_adjustment(self):
        self.pc.post(reverse('point_adjustment', args=[self.kid.pk]),
                         {'points_change': '-15', 'reason': 'oops'})
        self.kid.refresh_from_db()
        self.assertEqual(self.kid.points_balance, Decimal('85'))
        self.assertEqual(self.pc.post(reverse('point_adjustment', args=[self.parent.pk]),
                                      {'points_change': '5', 'reason': 'x'}).status_code, 302)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.points_balance, Decimal('0'))

    def test_reward_once_claimed_only_once(self):
        rw = models.Reward.objects.create(name='Icecream', points_cost=Decimal('20'),
                                          availability_type='once')
        self.cc.post(reverse('claim_reward', args=[rw.pk]))
        self.c2.post(reverse('claim_reward', args=[rw.pk]))
        self.kid.refresh_from_db(); self.kid2.refresh_from_db()
        self.assertEqual(self.kid.points_balance, Decimal('80'))
        self.assertEqual(self.kid2.points_balance, Decimal('100'))

    def test_parent_cannot_claim_reward_or_chore(self):
        rw = models.Reward.objects.create(name='X', points_cost=Decimal('1'))
        self.pc.post(reverse('claim_reward', args=[rw.pk]))
        rw.refresh_from_db()
        self.assertIsNone(rw.redeemed_by)

    def test_chore_form_assignment_type(self):
        f = forms.ChoreForm({'name': 'A', 'comment': '', 'points': '5', 'available': 'on',
                             'assignment_type': 'specific',
                             'assigned_children': [self.kid.pk], 'bonus_end_time': '14'})
        self.assertTrue(f.is_valid(), f.errors)
        ch = f.save()
        self.assertEqual(list(ch.assigned_children.all()), [self.kid])

        f2 = forms.EditChoreForm({'name': 'A', 'comment': '', 'points': '5', 'available': 'on',
                                  'assignment_type': 'any',
                                  'assigned_children': [self.kid.pk], 'bonus_end_time': '14'},
                                 instance=ch)
        self.assertTrue(f2.is_valid(), f2.errors)
        f2.save()
        self.assertEqual(list(ch.assigned_children.all()), [])

        f3 = forms.ChoreForm({'name': 'B', 'points': '0', 'assignment_type': 'any',
                              'bonus_end_time': '14'})
        self.assertFalse(f3.is_valid())
        f4 = forms.ChoreForm({'name': 'C', 'points': '5', 'assignment_type': 'specific',
                              'bonus_end_time': '14'})
        self.assertFalse(f4.is_valid())

    def test_edit_chore_form_initial(self):
        ch = models.Chore.objects.create(name='Z', points=Decimal('3'))
        self.assertEqual(forms.EditChoreForm(instance=ch)['assignment_type'].value(), 'any')
        ch.assigned_children.add(self.kid)
        self.assertEqual(forms.EditChoreForm(instance=ch)['assignment_type'].value(), 'specific')

    def test_nightly_reset(self):
        from chore_app.cron import reset_daily_chores
        d = models.Chore.objects.create(name='D', points=Decimal('2'), daily=True, available=False)
        models.ChoreClaim.objects.create(user=self.kid, chore_name='old', points=Decimal('2'),
                                         approved=Decimal('2'))
        pending = models.ChoreClaim.objects.create(user=self.kid, chore_name='p', points=Decimal('2'))
        reset_daily_chores()
        d.refresh_from_db()
        self.assertTrue(d.available)
        self.assertEqual(list(models.ChoreClaim.objects.all()), [pending])

    def test_parent_pages_render(self):
        for n in ('parent_profile', 'rewards_list', 'messages', 'create_chore', 'create_reward'):
            self.assertEqual(self.pc.get(reverse(n)).status_code, 200, n)
        self.assertEqual(self.cc.get(reverse('rewards_list')).status_code, 200)
        self.assertEqual(self.cc.get(reverse('child_chore')).status_code, 200)
        t = models.Text.objects.get(key='daily_message')
        self.assertEqual(self.pc.get(reverse('edit_text', args=[t.pk])).status_code, 200)
        ch = models.Chore.objects.create(name='E', points=Decimal('1'))
        self.assertEqual(self.pc.get(reverse('edit_chore', args=[ch.pk])).status_code, 200)
        self.assertEqual(self.pc.get(reverse('home')).status_code, 302)
