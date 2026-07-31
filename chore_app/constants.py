"""
Constants used throughout the chore application.
"""

# Early bonus: chores flagged `early_bonus` earn this extra percentage when
# claimed between EARLY_BONUS_START_HOUR and the chore's own bonus_end_time.
EARLY_BONUS_START_HOUR = 5
EARLY_BONUS_PERCENT = 25

# Pagination constants
POINT_LOGS_PER_PAGE = 20
CHILD_POINT_LOGS_PER_PAGE = 10

# Key of the Text row shown on the child dashboard
DAILY_MESSAGE_KEY = 'daily_message'
