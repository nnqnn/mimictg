from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    choose_type = State()
    public_url = State()
    private_posts = State()


class GenerationStates(StatesGroup):
    wait_topic = State()
    choose_post_type = State()


class ContentPlanStates(StatesGroup):
    wait_text = State()
    confirm = State()


class DailyPostStates(StatesGroup):
    wait_time = State()


class ScheduleStates(StatesGroup):
    wait_datetime = State()


class SettingsStates(StatesGroup):
    wait_channel_goal = State()
    wait_product_info = State()
    wait_tone = State()
    wait_emoji = State()
    wait_length = State()
    wait_timezone = State()


class PublishingStates(StatesGroup):
    wait_channel_binding = State()


class DeleteDataStates(StatesGroup):
    confirm = State()
