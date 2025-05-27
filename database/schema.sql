-- Admins Table
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Positions Table
CREATE TABLE positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Candidates Table
CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    class_name VARCHAR(50),
    gender VARCHAR(10),
    photo_url VARCHAR(255),
    position_id INT NOT NULL,
    role ENUM('candidate', 'winner', 'assistant') DEFAULT 'candidate',
    FOREIGN KEY (position_id) REFERENCES positions(id)
);

-- Voting Codes Table
CREATE TABLE voting_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    has_voted TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Votes Table
CREATE TABLE votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voting_code_id INT NOT NULL,
    candidate_id INT NOT NULL,
    position_id INT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voting_code_id) REFERENCES voting_codes(id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (position_id) REFERENCES positions(id)
);

-- Election Sessions Table
CREATE TABLE election_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT FALSE
);
