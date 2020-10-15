# Copyright (C) 1998
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

from .mbcharsetprober import MultiByteCharSetProber
from .codingstatemachine import CodingStateMachine
from .chardistribution import EUCTWDistributionAnalysis
from .mbcssm import EUCTW_SM_MODEL

class EUCTWProber(MultiByteCharSetProber):
    def __init__(self):
        super(EUCTWProber, self).__init__()
        self.coding_sm = CodingStateMachine(EUCTW_SM_MODEL)
        self.distribution_analyzer = EUCTWDistributionAnalysis()
        self.reset()

    @property
    def charset_name(self):
        return "EUC-TW"

    @property
    def language(self):
        return "Taiwan"
