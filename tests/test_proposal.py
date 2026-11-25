# SPDX-License-Identifier: BSD-3-Clause
"""What whyqd proposes a wrangler declare for a typed column, and that proposing changes nothing.

A proposal is a whole policy that whyqd has already read the column under: proposed where one reading reads every cell,
shown and not proposed where several do or none does.
"""

from whyqd.models import PolicyModel, ProposalModel, ReportModel


class TestForm:
    def test_a_field_s_policy_is_proposed_whole(self):
        policy = PolicyModel(format="dd/MM/yyyy", rules={"serial": "excel-1900"})
        proposal = ProposalModel(setting="policy", field="start", value=policy, evidence="Read every cell.")
        assert isinstance(proposal.value, PolicyModel)
        assert proposal.value == policy

    def test_a_policy_proposal_round_trips_through_the_report(self):
        policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
        report = ReportModel(
            path="data.csv",
            mime="text/csv",
            proposals=[ProposalModel(setting="policy", field="amount", value=policy, evidence="Read every cell.")],
        )
        again = ReportModel.model_validate_json(report.model_dump_json())
        assert again.proposals[0].value == policy

    def test_a_dialect_setting_is_proposed_as_before(self):
        proposal = ProposalModel(setting="delimiter", value=";", evidence="Every line splits alike.")
        assert proposal.value == ";"
