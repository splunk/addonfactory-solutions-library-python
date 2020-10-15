# Copyright (C) 1998
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from .mbcharsetprober import MultiByteCharSetProber
from .codingstatemachine import CodingStateMachine
from .chardistribution import Big5DistributionAnalysis
from .mbcssm import BIG5_SM_MODEL


class Big5Prober(MultiByteCharSetProber):
    def __init__(self):
        super(Big5Prober, self).__init__()
        self.coding_sm = CodingStateMachine(BIG5_SM_MODEL)
        self.distribution_analyzer = Big5DistributionAnalysis()
        self.reset()

    @property
    def charset_name(self):
        return "Big5"

    @property
    def language(self):
        return "Chinese"
