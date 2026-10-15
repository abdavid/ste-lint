def ids(fs):
    return [f.rule for f in fs]


def test_ing_form_flagged(lint):
    fs = lint("Removing the cover is not permitted.")
    assert "3.5" in ids(fs) and "1.4" not in ids(fs)


def test_ing_noun_in_dictionary_is_ok(lint):
    assert "3.5" not in ids(lint("Install the fitting."))


def test_passive_procedural_is_error(lint):
    [f] = [f for f in lint("The cover must be removed.", mode="procedural") if f.rule == "3.6"]
    assert f.severity == "error" and f.text == "removed"


def test_passive_descriptive_is_warning(lint):
    [f] = [f for f in lint("The cover is removed by the pump.", mode="descriptive") if f.rule == "3.6"]
    assert f.severity == "warning"


def test_active_not_flagged(lint):
    assert "3.6" not in ids(lint("Remove the cover.", mode="procedural"))


def test_noun_cluster_of_four(lint):
    fs = lint("Remove the fuel pump valve cover screw.", technical_nouns=set())
    [f] = [f for f in fs if f.rule == "2.1"]
    assert f.text == "fuel pump valve cover screw" and "5 words" in f.message


def test_noun_cluster_three_ok(lint):
    assert "2.1" not in ids(lint("Remove the fuel pump cover."))


def test_noun_cluster_allowlisted_multiword_counts_as_one(lint):
    fs = lint("Remove the fuel pump valve cover.", technical_nouns={"fuel pump/n"})
    assert "2.1" not in ids(fs)


def test_noun_cluster_hyphenated_compound_counts_as_one(lint):
    fs = lint("Remove the self-locking nut cover screw.")
    [f] = [f for f in fs if f.rule == "2.1"]
    assert f.text == "self-locking nut cover screw" and "4 words" in f.message


def test_noun_cluster_hyphenated_compound_alone_is_ok(lint):
    assert "2.1" not in ids(lint("Install the self-locking nut."))
