package test

default transfers = false

transfers {
	rules := [
		{
			input.method == "POST",
			any([input.roles[_] == "owner"]),
			input.params.amount >= 0,
		},
		{
			input.method == "POST",
			any([input.roles[_] == "beneficial_owner"]),
			input.params.amount >= 0,
			input.params.amount <= 10000,
		},
		{
			input.method == "POST",
			any([input.roles[_] == "power_of_attorney"]),
			input.params.amount >= 0,
			input.params.amount <= 5000,
		},
		{input.method == "GET"},
	]

	all(rules[_])
}

default accounts = false

accounts {
	rules := [
		{input.method == "GET"},
		{input.method == "POST"},
		{input.method == "DELETE"},
	]

	all(rules[_])
}
