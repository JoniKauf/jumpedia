USE jumpedia;

# SET foreign_key_checks = 0;
SET foreign_key_checks = 1;

CREATE TABLE IF NOT EXISTS location (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS location_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    location_id INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS location_parent (
    location_id INT NOT NULL,
    parent_id INT NOT NULL,
    PRIMARY KEY (location_id, parent_id),
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_id) REFERENCES location (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS location_tag (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tag VARCHAR(32) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS location_tags (
    location_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (location_id, tag_id),
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
    FOREIGN KEY (tag_id) REFERENCES location_tag (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tier (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(16) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS tier_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(16) UNIQUE NOT NULL,
    tier_id INT NOT NULL,
    FOREIGN KEY (tier_id) REFERENCES tier (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS difficulty (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(16) UNIQUE NOT NULL,
    tier_id INT,
    FOREIGN KEY (tier_id) REFERENCES tier (id)
);

CREATE TABLE IF NOT EXISTS difficulty_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    difficulty_id INT NOT NULL,
    alias VARCHAR(16) UNIQUE NOT NULL,
    FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS type (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) UNIQUE,
    description VARCHAR(512)
);


CREATE TABLE IF NOT EXISTS person (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS server (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS server_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    server_id INT NOT NULL,  
    FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS link (
	id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(512) UNIQUE NOT NULL,
    description VARCHAR(255),
    author INT NULL,
    FOREIGN KEY (author) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS extra (
	id INT AUTO_INCREMENT PRIMARY KEY,
    text VARCHAR(1024) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
);


CREATE TABLE IF NOT EXISTS tag (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tag VARCHAR(32) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
);

CREATE TABLE IF NOT EXISTS thumbnail (
	id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(512) UNIQUE NOT NULL
);


CREATE TABLE IF NOT EXISTS `rank` (
	power INT PRIMARY KEY,
    name VARCHAR(16)
);

# A user is an actual Jumpedia user while a
# person could be any finder, taser, prover ...
# A person must exist for a user to be defined
CREATE TABLE IF NOT EXISTS user (
    id BIGINT PRIMARY KEY,
    custom_name VARCHAR(64) NOT NULL,
    person_id INT NOT NULL,
    rank_power INT NOT NULL DEFAULT 0,
    FOREIGN KEY (person_id) REFERENCES person (id),
    FOREIGN KEY (rank_power) REFERENCES `rank` (power)
);



CREATE TABLE IF NOT EXISTS trickjump (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci,
    location_id INT NOT NULL,
    difficulty_id INT NOT NULL,
    type_id INT NOT NULL,
    found_at DATETIME NULL,
    tased_at DATETIME NULL,
    proven_at DATETIME NULL,
    server_id INT NOT NULL,
    thumbnail_id INT,
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
    FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE RESTRICT,
    FOREIGN KEY (type_id) REFERENCES type (id) ON DELETE RESTRICT,
    FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE RESTRICT,
    FOREIGN KEY (thumbnail_id) REFERENCES thumbnail (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_trickjump (
    trickjump_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    proof VARCHAR(512),
    given_at DATETIME,
    PRIMARY KEY (trickjump_id, user_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS trickjump_finder (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_taser (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_prover (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);



CREATE TABLE IF NOT EXISTS trickjump_extra (
	trickjump_id INT NOT NULL,
    extra_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, extra_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (extra_id) REFERENCES extra (id) ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS trickjump_tag (
    trickjump_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, tag_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_link (
    trickjump_id INT NOT NULL,
    link_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, link_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES link (id) ON DELETE RESTRICT
);



INSERT INTO tier (name) VALUES
('practice tier'),
('beginner'),
('intermediate'),
('advanced'),
('expert'),
('master'),
('low elite'),
('mid elite'),
('high elite'),
('insanity elite'),
('god tier'),
('hell tier'),
('unproven');

INSERT INTO tier_alias (alias, tier_id) VALUES
('practice', (SELECT id FROM tier WHERE name = 'practice tier')),
('beginner', (SELECT id FROM tier WHERE name = 'beginner')),
('intermediate', (SELECT id FROM tier WHERE name = 'intermediate')),
('advanced', (SELECT id FROM tier WHERE name = 'advanced')),
('expert', (SELECT id FROM tier WHERE name = 'expert')),
('master', (SELECT id FROM tier WHERE name = 'master')),
('low', (SELECT id FROM tier WHERE name = 'low elite')),
('mid', (SELECT id FROM tier WHERE name = 'mid elite')),
('high', (SELECT id FROM tier WHERE name = 'high elite')),
('insanity', (SELECT id FROM tier WHERE name = 'insanity elite')),
('god', (SELECT id FROM tier WHERE name = 'god tier')),
('hell', (SELECT id FROM tier WHERE name = 'hell tier'));


INSERT INTO difficulty (name, tier_id) VALUES
('0/10', (SELECT id FROM tier WHERE name = 'practice tier')),
('0.5/10', (SELECT id FROM tier WHERE name = 'beginner')),
('1/10', (SELECT id FROM tier WHERE name = 'beginner')),
('1.5/10', (SELECT id FROM tier WHERE name = 'beginner')),
('2/10', (SELECT id FROM tier WHERE name = 'beginner')),
('2.5/10', (SELECT id FROM tier WHERE name = 'beginner')),
('3/10', (SELECT id FROM tier WHERE name = 'beginner')),
('3.5/10', (SELECT id FROM tier WHERE name = 'intermediate')),
('4/10', (SELECT id FROM tier WHERE name = 'intermediate')),
('4.5/10', (SELECT id FROM tier WHERE name = 'intermediate')),
('5/10', (SELECT id FROM tier WHERE name = 'intermediate')),
('5.5/10', (SELECT id FROM tier WHERE name = 'advanced')),
('6/10', (SELECT id FROM tier WHERE name = 'advanced')),
('6.5/10', (SELECT id FROM tier WHERE name = 'advanced')),
('7/10', (SELECT id FROM tier WHERE name = 'expert')),
('7.5/10', (SELECT id FROM tier WHERE name = 'expert')),
('8/10', (SELECT id FROM tier WHERE name = 'expert')),
('8.5/10', (SELECT id FROM tier WHERE name = 'master')),
('9/10', (SELECT id FROM tier WHERE name = 'master')),
('9.5/10', (SELECT id FROM tier WHERE name = 'master')),
('10/10', (SELECT id FROM tier WHERE name = 'master')),
('low elite', (SELECT id FROM tier WHERE name = 'low elite')),
('mid elite', (SELECT id FROM tier WHERE name = 'mid elite')),
('high elite', (SELECT id FROM tier WHERE name = 'high elite')),
('insanity elite', (SELECT id FROM tier WHERE name = 'insanity elite')),
('god tier', (SELECT id FROM tier WHERE name = 'god tier')),
('hell tier', (SELECT id FROM tier WHERE name = 'hell tier')),
('unproven', (SELECT id FROM tier WHERE name = 'unproven'));


INSERT INTO difficulty_alias (alias, difficulty_id) VALUES
('0', (SELECT id FROM difficulty WHERE name = '0/10')),
('.5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
(',5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
('0.5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
('0,5', (SELECT id FROM difficulty WHERE name = '0.5/10')),
('.5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
(',5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
('0,5/10', (SELECT id FROM difficulty WHERE name = '0.5/10')),
('1', (SELECT id FROM difficulty WHERE name = '1/10')),
('1.5', (SELECT id FROM difficulty WHERE name = '1.5/10')),
('1,5', (SELECT id FROM difficulty WHERE name = '1.5/10')),
('1,5/10', (SELECT id FROM difficulty WHERE name = '1.5/10')),
('2', (SELECT id FROM difficulty WHERE name = '2/10')),
('2.5', (SELECT id FROM difficulty WHERE name = '2.5/10')),
('2,5', (SELECT id FROM difficulty WHERE name = '2.5/10')),
('2,5/10', (SELECT id FROM difficulty WHERE name = '2.5/10')),
('3', (SELECT id FROM difficulty WHERE name = '3/10')),
('3.5', (SELECT id FROM difficulty WHERE name = '3.5/10')),
('3,5', (SELECT id FROM difficulty WHERE name = '3.5/10')),
('3,5/10', (SELECT id FROM difficulty WHERE name = '3.5/10')),
('4', (SELECT id FROM difficulty WHERE name = '4/10')),
('4.5', (SELECT id FROM difficulty WHERE name = '4.5/10')),
('4,5', (SELECT id FROM difficulty WHERE name = '4.5/10')),
('4,5/10', (SELECT id FROM difficulty WHERE name = '4.5/10')),
('5', (SELECT id FROM difficulty WHERE name = '5/10')),
('5.5', (SELECT id FROM difficulty WHERE name = '5.5/10')),
('5,5', (SELECT id FROM difficulty WHERE name = '5.5/10')),
('5,5/10', (SELECT id FROM difficulty WHERE name = '5.5/10')),
('6', (SELECT id FROM difficulty WHERE name = '6/10')),
('6.5', (SELECT id FROM difficulty WHERE name = '6.5/10')),
('6,5', (SELECT id FROM difficulty WHERE name = '6.5/10')),
('6,5/10', (SELECT id FROM difficulty WHERE name = '6.5/10')),
('7', (SELECT id FROM difficulty WHERE name = '7/10')),
('7.5', (SELECT id FROM difficulty WHERE name = '7.5/10')),
('7,5', (SELECT id FROM difficulty WHERE name = '7.5/10')),
('7,5/10', (SELECT id FROM difficulty WHERE name = '7.5/10')),
('8', (SELECT id FROM difficulty WHERE name = '8/10')),
('8.5', (SELECT id FROM difficulty WHERE name = '8.5/10')),
('8,5', (SELECT id FROM difficulty WHERE name = '8.5/10')),
('8,5/10', (SELECT id FROM difficulty WHERE name = '8.5/10')),
('9', (SELECT id FROM difficulty WHERE name = '9/10')),
('9.5', (SELECT id FROM difficulty WHERE name = '9.5/10')),
('9,5', (SELECT id FROM difficulty WHERE name = '9.5/10')),
('9,5/10', (SELECT id FROM difficulty WHERE name = '9.5/10')),
('10', (SELECT id FROM difficulty WHERE name = '10/10')),
('low', (SELECT id FROM difficulty WHERE name = 'low elite')),
('mid', (SELECT id FROM difficulty WHERE name = 'mid elite')),
('high', (SELECT id FROM difficulty WHERE name = 'high elite')),
('insanity', (SELECT id FROM difficulty WHERE name = 'insanity elite')),
('god', (SELECT id FROM difficulty WHERE name = 'god tier')),
('hell', (SELECT id FROM difficulty WHERE name = 'hell tier'));


INSERT INTO location (name) VALUES
('cap kingdom'),
('cascade kingdom'),
('sand kingdom'),
('lake kingdom'),
('wooded kingdom'),
('cloud kingdom'),
('lost kingdom'),
('metro kingdom'),
('snow kingdom'),
('seaside kingdom'),
('luncheon kingdom'),
('ruined kingdom'),
('bowser''s kingdom'),
('moon kingdom'),
('mushroom kingdom'),
('dark side'),
('darker side');


INSERT INTO location_alias (alias, location_id) VALUES
('cap', (SELECT id FROM location WHERE name = 'cap kingdom')),
('cascade', (SELECT id FROM location WHERE name = 'cascade kingdom')),
('sand', (SELECT id FROM location WHERE name = 'sand kingdom')),
('lake', (SELECT id FROM location WHERE name = 'lake kingdom')),
('wooded', (SELECT id FROM location WHERE name = 'wooded kingdom')),
('cloud', (SELECT id FROM location WHERE name = 'cloud kingdom')),
('lost', (SELECT id FROM location WHERE name = 'lost kingdom')),
('metro', (SELECT id FROM location WHERE name = 'metro kingdom')),
('snow', (SELECT id FROM location WHERE name = 'snow kingdom')),
('seaside', (SELECT id FROM location WHERE name = 'seaside kingdom')),
('luncheon', (SELECT id FROM location WHERE name = 'luncheon kingdom')),
('ruined', (SELECT id FROM location WHERE name = 'ruined kingdom')),
('bowser', (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
('bowsers', (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
('bowser''s', (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
('bowser kingdom', (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
('bowsers kingdom', (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
('moon', (SELECT id FROM location WHERE name = 'moon kingdom')),
('mushroom', (SELECT id FROM location WHERE name = 'mushroom kingdom')),
('dark', (SELECT id FROM location WHERE name = 'dark side')),
('darker', (SELECT id FROM location WHERE name = 'darker side'));

INSERT INTO location (name) VALUES ('odyssey');

INSERT INTO location_parent (location_id, parent_id) VALUES
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'cap kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'cascade kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'sand kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'lake kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'wooded kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'cloud kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'lost kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'metro kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'snow kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'seaside kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'luncheon kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'ruined kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'bowser''s kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'moon kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'mushroom kingdom')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'dark Side')),
((SELECT id FROM location WHERE name = 'odyssey'), (SELECT id FROM location WHERE name = 'darker Side'));


INSERT INTO server (name) VALUES 
('smo trickjumping server'),
('database');

INSERT INTO server_alias (alias, server_id) VALUES
('main', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('main server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('main trickjump server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('main trickjumping server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('smo trickjump', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('smo trickjump server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('smo trickjumping', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('trickjump server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('trickjumping server', (SELECT id FROM server WHERE name = 'smo trickjumping server')),
('db', (SELECT id FROM server WHERE name = 'database')),
('database server', (SELECT id FROM server WHERE name = 'database')),
('smo database', (SELECT id FROM server WHERE name = 'database')),
('smo trickjumping database', (SELECT id FROM server WHERE name = 'database')),
('trickjump database', (SELECT id FROM server WHERE name = 'database')),
('trickjumping database', (SELECT id FROM server WHERE name = 'database')),
('trickjump db', (SELECT id FROM server WHERE name = 'database')),
('trickjumping db', (SELECT id FROM server WHERE name = 'database'));

INSERT IGNORE INTO location_tags (tag) VALUES ('Kingdom');

INSERT INTO location_to_tag (location_id, tag_id)
SELECT l.id, t.id
FROM location l
JOIN location_tags t ON t.tag = 'Kingdom'
WHERE l.name != 'Odyssey';