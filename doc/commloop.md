# Commloop
The commloop is a thing that MoMMI has to be sent messages over a regular TCP socket.
Stuff like GitHub webhooks relayed from a HTTP server.

**NOTE:** It's not actually a loop now, that's from the days I still used shitty multiprocessing for it.

# Protocol
Being a direct TCP socket, I need a protocol for fanciness reasons!

## Binary
 bytes     |  meaning
---------- | ---------
`0...2`    | Identifier bytes. If this doesn't match `\x30\x05` then MoMMI instantly drops connection.
`3...67`   | The HMAC digest, must be SHA-512.
`67...71`  | Big-endian unsigned 32 bit integer representing the length of the JSON message. This length is n.
`71...71+n` | UTF-8 encoded JSON as the message.

## JSON
 key    |  meaning
------  | ---------
`type`  | The type of message. This is used to know to which module to route the comm event.
`meta`  | Extra data used to identify route targets with along with type.
`cont`  | The actual content of the message. This can be anything and will be JSON decoded and passed to the relevant listeners.

### Example

```JSON
{
	"type": "github",
	"meta": "PJB3005/MoMMI",
	"cont": {
		"x": 10
	}
}
```

## Return codes
Codes MoMMI may or may not pass in a single byte to let you know how you screwed up the connection.
The code is passed in the lone byte of the return message. Endianness is big-endian.

 number  |  meaning
-------- | ---------
`0`      | Everything is good and MoMMI relayed the message.
`1`      | You didn't send the identifying bytes correctly.
`2`      | Packet structure is wrong or JSON decode failed.
`3`      | HMAC authentication failed.
