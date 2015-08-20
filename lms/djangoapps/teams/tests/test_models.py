# -*- coding: utf-8 -*-
"""Tests for the teams API at the HTTP request level."""
from datetime import datetime
import ddt
import itertools
from mock import Mock
import pytz

from django_comment_common.signals import (
    thread_created,
    thread_edited,
    thread_deleted,
    thread_voted,
    comment_created,
    comment_edited,
    comment_deleted,
    comment_voted,
    comment_endorsed
)
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from opaque_keys.edx.keys import CourseKey
from student.tests.factories import UserFactory

from .factories import CourseTeamFactory, CourseTeamMembershipFactory
from ..models import CourseTeam, CourseTeamMembership
from teams import TEAM_DISCUSSION_CONTEXT

COURSE_KEY1 = CourseKey.from_string('edx/history/1')
COURSE_KEY2 = CourseKey.from_string('edx/history/2')


@ddt.ddt
class TeamMembershipTest(SharedModuleStoreTestCase):
    """Tests for the TeamMembership model."""

    def setUp(self):
        """
        Set up tests.
        """
        super(TeamMembershipTest, self).setUp()

        self.user1 = UserFactory.create(username='user1')
        self.user2 = UserFactory.create(username='user2')

        self.team1 = CourseTeamFactory(course_id=COURSE_KEY1, team_id='team1')
        self.team2 = CourseTeamFactory(course_id=COURSE_KEY2, team_id='team2')

        self.team_membership11 = CourseTeamMembership(user=self.user1, team=self.team1)
        self.team_membership11.save()
        self.team_membership12 = CourseTeamMembership(user=self.user2, team=self.team1)
        self.team_membership12.save()
        self.team_membership21 = CourseTeamMembership(user=self.user1, team=self.team2)
        self.team_membership21.save()

    def test_membership_last_activity_set(self):
        current_last_activity = self.team_membership11.last_activity_at
        # Assert that the first save in the setUp sets a value.
        self.assertIsNotNone(current_last_activity)

        self.team_membership11.save()

        # Verify that we only change the last activity_at when it doesn't
        # already exist.
        self.assertEqual(self.team_membership11.last_activity_at, current_last_activity)

    @ddt.data(
        (None, None, None, 3),
        ('user1', None, None, 2),
        ('user1', [COURSE_KEY1], None, 1),
        ('user1', None, 'team1', 1),
        ('user2', None, None, 1),
    )
    @ddt.unpack
    def test_get_memberships(self, username, course_ids, team_id, expected_count):
        self.assertEqual(
            CourseTeamMembership.get_memberships(username=username, course_ids=course_ids, team_id=team_id).count(),
            expected_count
        )

    @ddt.data(
        ('user1', COURSE_KEY1, True),
        ('user2', COURSE_KEY1, True),
        ('user2', COURSE_KEY2, False),
    )
    @ddt.unpack
    def test_user_in_team_for_course(self, username, course_id, expected_value):
        user = getattr(self, username)
        self.assertEqual(
            CourseTeamMembership.user_in_team_for_course(user, course_id),
            expected_value
        )


@ddt.ddt
class TeamSignalsTest(SharedModuleStoreTestCase):
    """Tests for handling of team-related signals."""

    SIGNALS_LIST = (
        thread_created,
        thread_edited,
        thread_deleted,
        thread_voted,
        comment_created,
        comment_edited,
        comment_deleted,
        comment_voted,
        comment_endorsed
    )

    DISCUSSION_TOPIC_ID = 'test_topic'

    def setUp(self):
        """Create a user with a team to test signals."""
        super(TeamSignalsTest, self).setUp()
        self.user = UserFactory.create(username="user")
        self.moderator = UserFactory.create(username="moderator")
        self.team = CourseTeamFactory(discussion_topic_id=self.DISCUSSION_TOPIC_ID)
        self.team_membership = CourseTeamMembershipFactory(user=self.user, team=self.team)

    def mock_comment(self, context):
        """Create a mock comment service object with the given context."""
        return Mock(
            user_id=self.user.id,
            commentable_id=self.DISCUSSION_TOPIC_ID,
            context=context,
            **{'thread.user_id': self.user.id}
        )

    @ddt.data(
        *itertools.product(
            SIGNALS_LIST,
            (('user', True), ('moderator', False))
        )
    )
    @ddt.unpack
    def test_signals(self, signal, (user, should_update)):
        """Test that `last_activity_at` is correctly updated when team-related
        signals are sent.
        """
        team_last_activity = self.team.last_activity_at
        team_membership_last_activity = self.team_membership.last_activity_at
        user = getattr(self, user)
        signal.send(sender=None, user=user, post=self.mock_comment(TEAM_DISCUSSION_CONTEXT))
        team = CourseTeam.objects.get(id=self.team.id)  # pylint: disable=maybe-no-member
        team_membership = CourseTeamMembership.objects.get(id=self.team_membership.id)  # pylint: disable=maybe-no-member
        if should_update:
            self.assertGreater(team.last_activity_at, team_last_activity)
            self.assertGreater(team_membership.last_activity_at, team_membership_last_activity)
            now = datetime.utcnow().replace(tzinfo=pytz.utc)
            self.assertGreater(now, team.last_activity_at)
            self.assertGreater(now, team_membership.last_activity_at)
        else:
            self.assertEqual(team.last_activity_at, team_last_activity)
            self.assertEqual(team_membership.last_activity_at, team_membership_last_activity)

    @ddt.data(*SIGNALS_LIST)
    def test_signals_course_context(self, signal):
        """Test that `last_activity_at` is not updated when activity takes
        place in discussions outside of a team.
        """
        team_last_activity = self.team.last_activity_at
        team_membership_last_activity = self.team_membership.last_activity_at
        signal.send(sender=None, user=self.user, post=self.mock_comment('course'))
        team = CourseTeam.objects.get(id=self.team.id)  # pylint: disable=maybe-no-member
        team_membership = CourseTeamMembership.objects.get(id=self.team_membership.id)  # pylint: disable=maybe-no-member
        self.assertEqual(team_last_activity, team.last_activity_at)
        self.assertEqual(team_membership.last_activity_at, team_membership_last_activity)
