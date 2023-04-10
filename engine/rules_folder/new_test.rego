package test

default transfer = false

transfer {
	rules := [
		{
			any([input.roles[_] == "owner"]),
			input.payload.amount >= 0,
		},
		{
			any([input.roles[_] == "beneficial owner"]),
			input.payload.amount >= 0,
			input.payload.amount <= 10000,
		},
		{
			any([input.roles[_] == "power of attorney"]),
			input.payload.amount >= 0,
			input.payload.amount <= 5000,
		},
	]

	all(rules[_])
}
