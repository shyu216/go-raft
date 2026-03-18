# CUHK - Fall 2022 Raft Assignment

> **Disclaimer:** This is my coursework for CUHK - Fall 2022 Raft Assignment. Please do not copy my answers. Solve the problems yourself to truly understand Raft and Go — that's the whole point of the assignment!

This repository documents my first hands-on experience with **Go** and my exploration of the **Raft consensus algorithm**.

### Why This Matters to Me

Before this assignment, I had never written a single line of Go. Coming from other programming languages, Go's concurrency model and clean syntax were refreshing but also challenging at first. The `goroutine` and `channel` concepts took some time to sink in.

Raft, on the other hand, was a completely new concept to me. Understanding how a distributed system achieves consensus — leader election, log replication, safety guarantees — was both exciting and mind-bending. The algorithm is elegant in its design, yet implementing it reveals countless edge cases and subtle timing issues.

### What I've Learned

- **Go Basics**: Building, importing packages, working with `go.mod`
- **gRPC**: Defining protobuf messages and generating Go code
- **Raft Protocol**:
  - Leader election (term, vote, timeout)
  - Log replication
  - State machine safety

### New Additions

- Resolved dependency path issues in the project
- Added PowerShell scripts for running tests on Windows

### Test Results

```
=== Test Results ===
2026/03/18 22:16:16 testOneCandidateStartTwoElection PASS
2026/03/18 22:16:31 testTwoCandidateForElection PASS
2026/03/18 22:16:46 testSplitVote PASS
2026/03/18 22:16:59 testAllForElection PASS
2026/03/18 22:17:13 testLeaderRevertToFollower PASS
2026/03/18 22:17:44 testOneSimpleDelete PASS
All tests completed.
```
