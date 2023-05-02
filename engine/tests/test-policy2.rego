package test

default transfers = false

transfers {
	rules := [
		{
			input.method == "POST",
			any([input.roles[_] == "Owner"]),
			input.params.amount >= 0,
		},
		{
			input.method == "POST",
			any([input.roles[_] == "Beneficial Owner"]),
			input.params.amount >= 0,
			input.params.amount <= 10000,
		},
		{
			input.method == "POST",
			any([input.roles[_] == "Power of Attorney"]),
			input.params.amount >= 0,
			input.params.amount <= 15000,
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
