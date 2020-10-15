# Copyright (C) 1998
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from .mbcharsetprober import MultiByteCharSetProber
from .codingstatemachine import CodingStateMachine
from .chardistribution import GB2312DistributionAnalysis
from .mbcssm import GB2312_SM_MODEL

class GB2312Prober(MultiByteCharSetProber):
    def __init__(self):
        super(GB2312Prober, self).__init__()
        self.coding_sm = CodingStateMachine(GB2312_SM_MODEL)
        self.distribution_analyzer = GB2312DistributionAnalysis()
        self.reset()

    @property
    def charset_name(self):
        return "GB2312"

    @property
    def language(self):
        return "Chinese"
