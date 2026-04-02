from ai_mv.cli.args import build_parser
from ai_mv.core.orchestration.config_defaults import default_config


def test_parser_has_clean_commands():
    parser = build_parser()
    names = parser._subparsers._group_actions[0].choices.keys()  # type: ignore[attr-defined]
    assert "start" in names
    assert "preflight" in names
    assert "ref-probe" in names


def test_default_config_uses_brief_not_profile():
    cfg = default_config()
    assert "brief" in cfg
    assert "profile" not in cfg


def test_preflight_accepts_brief():
    parser = build_parser()
    args = parser.parse_args(["preflight", "--brief", "director_brief_example"])
    assert args.brief == "director_brief_example"


def test_start_accepts_brief():
    parser = build_parser()
    args = parser.parse_args(["start", "--brief", "director_brief_example"])
    assert args.brief == "director_brief_example"


def test_ref_probe_accepts_required_inputs():
    parser = build_parser()
    args = parser.parse_args(
        [
            "ref-probe",
            "--brief",
            "director_brief_example",
            "--ref",
            "anchor.png",
            "--prompt",
            "The same heroine crosses the wet curb.",
        ]
    )
    assert args.brief == "director_brief_example"
    assert args.ref == "anchor.png"
    assert args.prompt == "The same heroine crosses the wet curb."


def test_ref_probe_batch_accepts_required_inputs():
    parser = build_parser()
    args = parser.parse_args(
        [
            "ref-probe-batch",
            "--brief",
            "director_brief_example",
            "--ref",
            "anchor.png",
            "--prompts-file",
            "prompts.txt",
        ]
    )
    assert args.brief == "director_brief_example"
    assert args.ref == "anchor.png"
    assert args.prompts_file == "prompts.txt"
