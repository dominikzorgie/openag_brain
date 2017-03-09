#!/usr/bin/python
import rospy

from std_msgs.msg import Float64
from openag.var_types import EnvVar, GROUP_ENVIRONMENT

# Filter a list of environmental variables that are specific to environment
# sensors and actuators
ENVIRONMENT_VARIABLES = tuple(
    var for var in EnvVar.items.values()
    if GROUP_ENVIRONMENT in var.groups
)


class EWMA(object):
    """
    Calculate the Exponentially Weighted Moving Average (EWMA) for an input variable.
    EWMAi = alpha * Xi + (1 - alpha) * EWMAi-1
    Params:
        a : Alpha is the dapening coefficient. The lower the value the less damped. Should be between 0 and 1
    """
    def __init__(self, a):
        self.a = a
        self.average = None

    def __call__(self, sample):
        """
        Returns the recent moving average based on the latest data point.
        :param sample: The most recent data point.
        :return: The latest moving average data point (EWMAi)
        """
        # Update the average
        if self.average is None:
            self.average = sample
            return
        self.average = self.a * sample + (1 - self.a) * self.average


def filter_topic(src_topic, dest_topic, topic_type):
    """
    Publishes a measured data point given the raw value by applying the EWMA function to the data.
    :param src_topic: String? - Source topic signal to be filtered
    :param dest_topic: String? - Output topic to publish new data to
    :param topic_type: The data type of the topic, aka Float64, Int32, etc
    :return: sub, pub : subscribed topic (raw measured value) and published topic (filtered (smoothed) value)
    """
    rospy.loginfo("Filtering topic {} to topic {}".format(
        src_topic, dest_topic
    ))
    pub = rospy.Publisher(dest_topic, topic_type, queue_size=10)
    f = EWMA(0.3)

    def callback(src_item):
        f(src_item.data)
        dest_item = topic_type(f.average)
        pub.publish(dest_item)
    sub = rospy.Subscriber(src_topic, topic_type, callback)
    return sub, pub


def filter_all_variable_topics(variables):
    """
    Given an iterator publishers, where each publisher is a two-tuple
    `(topic, type)`, publishes a filtered topic endpoint.
    """
    for env_var in variables:
        src_topic = "{}/raw".format(env_var)
        dest_topic = "{}/measured".format(env_var)
        # Ignore type associated with environmental variable type and
        # coerce to Float64
        filter_topic(src_topic, dest_topic, Float64)

if __name__ == '__main__':
    rospy.init_node("topic_filter")
    # Make sure that we're under an environment namespace.
    filter_all_variable_topics(ENVIRONMENT_VARIABLES)
    rospy.spin()
