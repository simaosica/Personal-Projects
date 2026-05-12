import { useEffect, useState } from "react";
import "./App.css";

type Group = {
  id: number;
  name: string;
};

type Bet = {
  id: number;
  groupId: number;
  event: string;
  odds: number;
  stake: number;
  status: "pending" | "won" | "lost";
};

function calculateBetProfit(bet: Bet) {
  if (bet.status === "won") {
    return bet.stake * bet.odds - bet.stake;
  }

  if (bet.status === "lost") {
    return -bet.stake;
  }

  return 0;
}

function getProfitClassName(profit: number) {
  if (profit > 0) return "profit-positive";
  if (profit < 0) return "profit-negative";
  return "profit-neutral";
}

function App() {
  const [groupName, setGroupName] = useState("");
  const [isCreateGroupModalOpen, setIsCreateGroupModalOpen] = useState(false);
  const [isAddBetModalOpen, setIsAddBetModalOpen] = useState(false);

  const [groups, setGroups] = useState<Group[]>(() => {
    const savedGroups = localStorage.getItem("groups");

    if (savedGroups) {
      return JSON.parse(savedGroups);
    }

    return [];
  });

  const [bets, setBets] = useState<Bet[]>(() => {
    const savedBets = localStorage.getItem("bets");

    if (savedBets) {
      return JSON.parse(savedBets);
    }

    return [];
  });

  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [eventName, setEventName] = useState("");
  const [odds, setOdds] = useState("");
  const [stake, setStake] = useState("");
  const [status, setStatus] = useState<"pending" | "won" | "lost">("pending");

  const totalProfit = bets.reduce((total, bet) => {
    return total + calculateBetProfit(bet);
  }, 0);

  const totalBets = bets.length;
  const wonBets = bets.filter((bet) => bet.status === "won").length;
  const lostBets = bets.filter((bet) => bet.status === "lost").length;
  const pendingBets = bets.filter((bet) => bet.status === "pending").length;

  const totalStake = bets
    .filter((bet) => bet.status !== "pending")
    .reduce((total, bet) => {
      return total + bet.stake;
    }, 0);

  const roi = totalStake > 0 ? (totalProfit / totalStake) * 100 : 0;

  useEffect(() => {
    localStorage.setItem("groups", JSON.stringify(groups));
  }, [groups]);

  useEffect(() => {
    localStorage.setItem("bets", JSON.stringify(bets));
  }, [bets]);

  function createGroup() {
    if (groupName.trim() === "") return;

    const newGroup = {
      id: Date.now(),
      name: groupName.trim(),
    };

    setGroups([...groups, newGroup]);
    setGroupName("");
    setIsCreateGroupModalOpen(false);
  }

  function addBet() {
    if (selectedGroupId === "") return;
    if (eventName.trim() === "") return;
    if (odds === "") return;
    if (stake === "") return;
    if (Number(odds) <= 1) return;
    if (Number(stake) <= 0) return;

    const newBet = {
      id: Date.now(),
      groupId: Number(selectedGroupId),
      event: eventName.trim(),
      odds: Number(odds),
      stake: Number(stake),
      status: status,
    };

    setBets([...bets, newBet]);

    setSelectedGroupId("");
    setEventName("");
    setOdds("");
    setStake("");
    setStatus("pending");
    setIsAddBetModalOpen(false);
  }

  function deleteGroup(groupId: number) {
    setGroups(groups.filter((group) => group.id !== groupId));
    setBets(bets.filter((bet) => bet.groupId !== groupId));
  }

  function closeAddBetModal() {
    setSelectedGroupId("");
    setEventName("");
    setOdds("");
    setStake("");
    setStatus("pending");
    setIsAddBetModalOpen(false);
  }

  return (
    <main>
      <header className="app-header">
        <div>
          <h1>
            Bet<span className="brand-highlight">Portfolio</span>
          </h1>
          <p>Track. Analyze. Grow your betting edge.</p>
        </div>

        <div className="header-actions">
          <button className="blue-button" onClick={() => setIsAddBetModalOpen(true)}>
            Add Bet
          </button>

          <button className="blue-button" onClick={() => setIsCreateGroupModalOpen(true)}>
            Create Group
          </button>
        </div>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">↗</div>
          <div>
            <p>Total Profit</p>
            <h2 className={getProfitClassName(totalProfit)}>
              €{totalProfit.toFixed(2)}
            </h2>
            <span>All time</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">%</div>
          <div>
            <p>ROI</p>
            <h2 className={getProfitClassName(roi)}>{roi.toFixed(1)}%</h2>
            <span>Settled bets only</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">▣</div>
          <div>
            <p>Total Bets</p>
            <h2>{totalBets}</h2>
            <span>
              {wonBets} won / {lostBets} lost / {pendingBets} pending
            </span>
          </div>
        </div>
      </section>

      <section className="chart-card">
        <div className="chart-header">
          <h2>Cumulative Profit</h2>

          <select>
            <option>All Groups</option>
          </select>
        </div>

        <div className="chart-placeholder">
          <div className="fake-chart-line"></div>
          <p>Profit chart coming soon</p>
        </div>
      </section>

      <section className="groups-section">
        <div className="section-header">
          <h2>Your Groups</h2>
          <button className="secondary-button">View All Groups →</button>
        </div>

        {groups.length === 0 && (
          <div className="empty-card">
            <h3>No groups yet</h3>
            <p>Create your first group to start tracking your bets.</p>
            <button onClick={() => setIsCreateGroupModalOpen(true)}>
              Create Group
            </button>
          </div>
        )}

        <div className="groups-grid">
          {groups.map((group) => {
            const groupBets = bets.filter((bet) => bet.groupId === group.id);

            const groupProfit = groupBets.reduce((total, bet) => {
              return total + calculateBetProfit(bet);
            }, 0);

            const groupStake = groupBets
              .filter((bet) => bet.status !== "pending")
              .reduce((total, bet) => {
                return total + bet.stake;
              }, 0);

            const groupRoi =
              groupStake > 0 ? (groupProfit / groupStake) * 100 : 0;

            const groupWonBets = groupBets.filter(
              (bet) => bet.status === "won"
            ).length;

            const groupLostBets = groupBets.filter(
              (bet) => bet.status === "lost"
            ).length;

            const groupPendingBets = groupBets.filter(
              (bet) => bet.status === "pending"
            ).length;

            return (
              <div className="group-card" key={group.id}>
                <div className="group-card-header">
                  <div className="group-title-row">
                    <div className="group-icon">📊</div>

                    <div>
                      <h3>{group.name}</h3>
                      <span>{groupBets.length} bets</span>
                    </div>
                  </div>

                  <button
                    className="icon-button"
                    onClick={() => deleteGroup(group.id)}
                  >
                    ⋮
                  </button>
                </div>

                <div className="group-stats">
                  <div>
                    <p>Profit</p>
                    <strong className={getProfitClassName(groupProfit)}>
                      €{groupProfit.toFixed(2)}
                    </strong>
                  </div>

                  <div>
                    <p>ROI</p>
                    <strong className={getProfitClassName(groupRoi)}>
                      {groupRoi.toFixed(1)}%
                    </strong>
                  </div>

                  <div>
                    <p>Bets</p>
                    <strong>{groupBets.length}</strong>
                  </div>
                </div>

                <div className="group-results">
                  <span className="won-dot">Won {groupWonBets}</span>
                  <span className="lost-dot">Lost {groupLostBets}</span>
                  <span className="pending-dot">
                    Pending {groupPendingBets}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {isCreateGroupModalOpen && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>Create Group</h2>

            <label>Group name</label>
            <input
              type="text"
              placeholder="Example: BTTS"
              value={groupName}
              onChange={(event) => setGroupName(event.target.value)}
            />

            <div className="modal-actions">
              <button
                className="secondary-button"
                onClick={() => {
                  setGroupName("");
                  setIsCreateGroupModalOpen(false);
                }}
              >
                Cancel
              </button>

              <button onClick={createGroup}>Create</button>
            </div>
          </div>
        </div>
      )}

      {isAddBetModalOpen && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>Add Bet</h2>

            <label>Group</label>
            <select
              value={selectedGroupId}
              onChange={(event) => setSelectedGroupId(event.target.value)}
            >
              <option value="">Select group</option>

              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>

            <label>Event</label>
            <input
              type="text"
              placeholder="Benfica vs Porto"
              value={eventName}
              onChange={(event) => setEventName(event.target.value)}
            />

            <label>Odds</label>
            <input
              type="number"
              step="0.01"
              min="1.01"
              placeholder="1.85"
              value={odds}
              onChange={(event) => setOdds(event.target.value)}
            />

            <label>Stake</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="10"
              value={stake}
              onChange={(event) => setStake(event.target.value)}
            />

            <label>Status</label>
            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as "pending" | "won" | "lost")
              }
            >
              <option value="pending">Pending</option>
              <option value="won">Won</option>
              <option value="lost">Lost</option>
            </select>

            <div className="modal-actions">
              <button className="secondary-button" onClick={closeAddBetModal}>
                Cancel
              </button>

              <button onClick={addBet}>Add Bet</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default App;