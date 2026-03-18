module cuhk/asgn

go 1.13

require (
	cuhk/asgn/raft v0.0.0
	google.golang.org/grpc v1.24.0
)

replace cuhk/asgn/raft => ../tests/raft
