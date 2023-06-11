
#define ceil(x) (-round(-(x)))
#define floor(x) round(x)
#define clamp(x, low, high) max((low),min((high),(x)))

#define BENCH(NAME, ITERS, CODE) \
	do{ \
		var/s = world.timeofday ;\
		for(var/i = 1 to (ITERS)) {\
			CODE ;\
		} ;\
		var/e = world.timeofday ;\
		world.log << "[NAME]: [e-s] ds" ;\
	} while(0)
#define BENCHK(NAME, ITERS, CODE) \
	do{ \
		var/s = world.timeofday ;\
		for(var/j = 1 to 1000) {\
		for(var/i = 1 to (ITERS)) {\
			CODE ;\
		} ;\
		} ;\
		var/e = world.timeofday ;\
		world.log << "[NAME]: [e-s] ds" ;\
	} while(0)
#define BENCHM(NAME, ITERS, CODE) \
	do{ \
		var/s = world.timeofday ;\
		for(var/j = 1 to 1000000) {\
		for(var/i = 1 to (ITERS)) {\
			CODE ;\
		} ;\
		} ;\
		var/e = world.timeofday ;\
		world.log << "[NAME]: [e-s] ds" ;\
	} while(0)

/proc/ffold() return ffoldl(arglist(args))
/proc/ffoldl(proc, list/L, initial=L)
	var/x = initial
	var/start = 1
	if(x == L)
		x = L[1]
		start = 2

	for(var/i = start to L.len)
		x = call(proc)(x, L[i])

	return x

/proc/ffoldr(proc, list/L, initial=L)
	var/x = initial
	var/start = L.len
	if(x == L)
		x = L[L.len]
		start = L.len - 1

	for(var/i = start to 1 step -1)
		x = call(proc)(x, L[i])

	return x

/proc/fmap(proc, list/L)
	for(var/x = 1 to L.len)
		L[x] = call(proc)(L[x])
	return L

/proc/ffilter(proc, list/L)
	var/x = 1
	while(x <= L.len)
		if(call(proc)(L[x]))
			x++
		else
			L.Cut(x, x+1)
	return L

/proc/stars(n, pr)
	if (pr == null)
		pr = 25
	if (pr < 0)
		return null
	else
		if (pr >= 100)
			return n
	var/te = n
	var/t = ""
	n = length(n)
	var/p = null
	p = 1
	var/intag = 0
	while(p <= n)
		var/char = copytext(te, p, p + 1)
		if (char == "<") //let's try to not break tags
			intag = !intag
		if (intag || char == " " || prob(pr))
			t = text("[][]", t, char)
		else
			t = text("[]*", t)
		if (char == ">")
			intag = !intag
		p++
	return t

/proc/seq(lo, hi, st=1)
	if(isnull(hi))
		hi = lo
		lo = 1

	. = list()
	for(var/x in lo to hi step st)
		. += x