module cuhk/tests

go 1.13

require (
	cuhk/tests/raft v0.0.0
	google.golang.org/grpc v1.24.0
)

replace cuhk/tests/raft => ./raft
