package test

default transfers = false

transfers {
	rules := [
		{
			input.method == "POST",
			any([input.roles[_] == "owner", input.roles[_] == "attorney"]),
			input.params.amount >= 0,
			input.params.amount <= 500,
		},
		{
			input.method == "POST",
			any([input.roles[_] == "partial_owner"]),
			input.params.amount >= 0,
			input.params.amount <= 100,
		},
	]

	all(rules[_])
}
